"""Synthetic test data generator using LLM."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Sequence

from ragmax.evaluation.models import EvalTestCase
from ragmax.infrastructure.llm.client import LLMClient, LLMMessage


class SyntheticDataGenerator:
    """
    Generate synthetic test cases from documents using LLM.

    Uses LLM to analyze document content and generate realistic
    question-answer pairs for evaluation purposes.
    """

    def __init__(self, llm_client: LLMClient):
        """
        Args:
            llm_client: LLM client for generating synthetic data
        """
        self.llm = llm_client

    async def generate_from_documents(
        self,
        documents: list[tuple[str, str]],  # (doc_id, doc_content)
        num_cases_per_doc: int = 5,
        difficulty: str = "mixed",  # "easy", "medium", "hard", "mixed"
        language: str = "zh",  # "zh", "en"
    ) -> list[EvalTestCase]:
        """
        Generate test cases from a list of documents.

        Args:
            documents: List of (doc_id, content) tuples
            num_cases_per_doc: Number of test cases to generate per document
            difficulty: Difficulty level or "mixed" for variety
            language: Language for questions ("zh" or "en")

        Returns:
            List of generated EvalTestCase instances
        """

        tasks = []
        for doc_id, content in documents:
            task = self._generate_from_single_doc(
                doc_id=doc_id,
                content=content,
                num_cases=num_cases_per_doc,
                difficulty=difficulty,
                language=language,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and filter successful results
        all_cases = []
        for result in results:
            if isinstance(result, list):
                all_cases.extend(result)

        return all_cases

    async def _generate_from_single_doc(
        self,
        doc_id: str,
        content: str,
        num_cases: int,
        difficulty: str,
        language: str,
    ) -> list[EvalTestCase]:
        """Generate test cases from a single document."""

        # Truncate very long documents
        max_content_length = 4000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "\n...(内容已截断)"

        # Build prompt based on language
        if language == "zh":
            prompt = self._build_chinese_prompt(content, num_cases, difficulty)
        else:
            prompt = self._build_english_prompt(content, num_cases, difficulty)

        messages: Sequence[LLMMessage] = [{"role": "user", "content": prompt}]

        try:
            response = await self.llm.generate(messages, temperature=0.7, max_tokens=2000)

            # Parse JSON response
            qa_pairs = json.loads(response.content)

            if not isinstance(qa_pairs, list):
                return []

            # Convert to EvalTestCase objects
            test_cases = []
            for idx, pair in enumerate(qa_pairs[:num_cases]):
                if not isinstance(pair, dict) or "question" not in pair or "answer" not in pair:
                    continue

                test_case = EvalTestCase(
                    id=f"syn_{doc_id}_{uuid.uuid4().hex[:6]}",
                    question=pair["question"],
                    expected_answer=pair["answer"],
                    ground_truth_docs=[doc_id],
                    metadata={
                        "difficulty": pair.get("difficulty", "medium"),
                        "synthetic": True,
                        "source_doc": doc_id,
                        "language": language,
                        "category": pair.get("category", "general"),
                    },
                    created_at=datetime.now(),
                )
                test_cases.append(test_case)

            return test_cases

        except (json.JSONDecodeError, Exception):
            # Failed to generate, return empty list
            return []

    def _build_chinese_prompt(self, content: str, num_cases: int, difficulty: str) -> str:
        """Build Chinese prompt for generating test cases."""

        difficulty_instructions = {
            "easy": "简单难度：问题应该是直接的事实查询，答案可以直接从文档中找到。",
            "medium": "中等难度：问题需要理解和简单推理，答案需要综合文档中的信息。",
            "hard": "困难难度：问题需要深入理解和复杂推理，答案需要综合多处信息并进行推断。",
            "mixed": "混合难度：生成不同难度级别的问题，包括简单、中等和困难。",
        }

        return f"""基于以下文档内容，生成 {num_cases} 个高质量的问答对，用于评估 RAG 系统。

文档内容:
{content}

要求:
1. {difficulty_instructions.get(difficulty, difficulty_instructions["mixed"])}
2. 问题应该是用户可能会问的自然问题
3. 答案必须完全基于文档内容，不要编造信息
4. 问题应该覆盖文档的不同方面
5. 每个问答对应该标注难度级别（easy/medium/hard）和类别

以 JSON 数组格式返回，每个对象包含以下字段:
- question: 问题文本
- answer: 答案文本
- difficulty: 难度级别（easy/medium/hard）
- category: 问题类别（如：定义、步骤、原因、比较等）

示例格式:
[
  {{
    "question": "什么是...?",
    "answer": "...是...",
    "difficulty": "easy",
    "category": "定义"
  }}
]

只返回 JSON 数组，不要其他内容。"""

    def _build_english_prompt(self, content: str, num_cases: int, difficulty: str) -> str:
        """Build English prompt for generating test cases."""

        difficulty_instructions = {
            "easy": "Easy: Questions should be direct factual queries with answers directly stated in the document.",
            "medium": "Medium: Questions require understanding and simple reasoning, answers need to synthesize information.",
            "hard": "Hard: Questions require deep understanding and complex reasoning, answers need to integrate multiple pieces of information.",
            "mixed": "Mixed: Generate questions at different difficulty levels including easy, medium, and hard.",
        }

        return f"""Based on the following document content, generate {num_cases} high-quality question-answer pairs for evaluating a RAG system.

Document content:
{content}

Requirements:
1. {difficulty_instructions.get(difficulty, difficulty_instructions["mixed"])}
2. Questions should be natural questions that users might ask
3. Answers must be entirely based on the document content, do not make up information
4. Questions should cover different aspects of the document
5. Each QA pair should be tagged with difficulty level (easy/medium/hard) and category

Return as a JSON array with the following fields for each object:
- question: Question text
- answer: Answer text
- difficulty: Difficulty level (easy/medium/hard)
- category: Question category (e.g., definition, procedure, reason, comparison, etc.)

Example format:
[
  {{
    "question": "What is...?",
    "answer": "...is...",
    "difficulty": "easy",
    "category": "definition"
  }}
]

Return only the JSON array, no other content."""
