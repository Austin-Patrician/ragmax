"""Generation-layer evaluation metrics using LLM-as-a-judge."""

import json
from typing import Sequence

from ragmax.evaluation.metrics import Metric
from ragmax.evaluation.models import EvalTestCase, GenerationResult, RetrievalResult
from ragmax.infrastructure.llm.client import LLMClient, LLMMessage


class FaithfulnessMetric(Metric):
    """
    Faithfulness: Whether the generated answer is supported by retrieved context.

    Uses LLM to:
    1. Extract claims from the answer
    2. Verify each claim is supported by the context

    Score = supported_claims / total_claims
    """

    def __init__(self, llm_client: LLMClient, doc_store=None):
        self.llm = llm_client
        self.doc_store = doc_store

    @property
    def name(self) -> str:
        return "faithfulness"

    @property
    def requires_llm(self) -> bool:
        return True

    @property
    def threshold(self) -> float:
        return 0.95

    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        if not generation_result or not generation_result.answer:
            return 0.0

        if not retrieval_result or not retrieval_result.retrieved_doc_ids:
            return 0.0

        # 1. Extract claims from answer
        claims = await self._extract_claims(generation_result.answer)

        if not claims:
            return 1.0  # No claims to verify

        # 2. Get context from retrieved documents
        context = await self._get_context(retrieval_result.retrieved_doc_ids)

        # 3. Verify each claim
        supported_count = 0
        for claim in claims:
            is_supported = await self._verify_claim(claim, context)
            if is_supported:
                supported_count += 1

        return supported_count / len(claims)

    async def _extract_claims(self, answer: str) -> list[str]:
        """Use LLM to extract independent claims from answer."""

        prompt = f"""分解以下答案为独立的事实陈述列表。每个陈述应该是一个可以独立验证的事实。

答案: {answer}

以 JSON 数组格式返回: ["陈述1", "陈述2", ...]

只返回 JSON 数组，不要其他内容。"""

        messages: Sequence[LLMMessage] = [{"role": "user", "content": prompt}]

        try:
            response = await self.llm.generate(messages, temperature=0.0)
            # Parse JSON array
            claims = json.loads(response.content)
            return claims if isinstance(claims, list) else []
        except (json.JSONDecodeError, Exception):
            # Fallback: split by sentences
            return [s.strip() for s in answer.split("。") if s.strip()]

    async def _verify_claim(self, claim: str, context: str) -> bool:
        """Use LLM to verify if claim is supported by context."""

        prompt = f"""判断以下陈述是否被上下文支持。

上下文:
{context}

陈述: {claim}

如果陈述的内容可以从上下文中推断出来或直接找到，回答 "YES"。
如果陈述的内容与上下文矛盾或无法从上下文中得出，回答 "NO"。

只回答 "YES" 或 "NO"，不要其他内容。"""

        messages: Sequence[LLMMessage] = [{"role": "user", "content": prompt}]

        try:
            response = await self.llm.generate(messages, temperature=0.0, max_tokens=10)
            return "YES" in response.content.upper()
        except Exception:
            return False

    async def _get_context(self, doc_ids: list[str]) -> str:
        """Get concatenated context from document IDs."""

        if not self.doc_store:
            # Fallback: return doc IDs as context
            return "\n".join(doc_ids)

        # TODO: Fetch actual document content from doc_store
        # For now, return doc IDs
        return "\n".join(doc_ids)


class AnswerRelevancyMetric(Metric):
    """
    Answer Relevancy: How well the answer addresses the question.

    Uses LLM to judge if the answer is relevant and helpful
    for answering the user's question.

    Score: 0.0 (not relevant) to 1.0 (highly relevant)
    """

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    @property
    def name(self) -> str:
        return "answer_relevancy"

    @property
    def requires_llm(self) -> bool:
        return True

    @property
    def threshold(self) -> float:
        return 0.85

    async def compute(
        self,
        test_case: EvalTestCase,
        retrieval_result: RetrievalResult,
        generation_result: GenerationResult,
    ) -> float:
        if not generation_result or not generation_result.answer:
            return 0.0

        prompt = f"""评估以下答案对问题的相关性和有用性。

问题: {test_case.question}

答案: {generation_result.answer}

评分标准:
- 1.0: 答案完全回答了问题，信息准确且有用
- 0.8: 答案基本回答了问题，但可能缺少一些细节
- 0.6: 答案部分相关，但不够完整
- 0.4: 答案相关性较低
- 0.2: 答案几乎不相关
- 0.0: 答案完全不相关

只返回一个 0.0 到 1.0 之间的数字，不要其他内容。"""

        messages: Sequence[LLMMessage] = [{"role": "user", "content": prompt}]

        try:
            response = await self.llm.generate(messages, temperature=0.0, max_tokens=10)
            # Extract number from response
            score_str = response.content.strip()
            score = float(score_str)
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
        except (ValueError, Exception):
            # Fallback: basic keyword matching
            return self._fallback_relevancy(test_case.question, generation_result.answer)

    def _fallback_relevancy(self, question: str, answer: str) -> float:
        """Fallback relevancy check using keyword overlap."""

        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())

        if not question_words:
            return 0.5

        overlap = question_words & answer_words
        return min(1.0, len(overlap) / len(question_words))
