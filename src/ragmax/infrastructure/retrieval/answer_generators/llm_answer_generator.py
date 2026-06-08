"""LLM-based answer generator."""

import re
from collections.abc import Sequence

from ragmax.application.retrieval.dtos import GeneratedAnswer, RetrievalContextItem
from ragmax.infrastructure.llm.client import LLMClient, LLMMessage


class LLMAnswerGenerator:
    """LLM-based answer generator with citation tracking."""

    name = "llm_answer_generator:v1"

    def __init__(
        self,
        llm_client: LLMClient,
        max_context_items: int = 8,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> None:
        """Initialize LLM answer generator.

        Args:
            llm_client: LLM client for generation
            max_context_items: Maximum context items to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        """
        self.llm = llm_client
        self.max_context_items = max(1, max_context_items)
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def generate(
        self,
        *,
        query: str,
        contexts: Sequence[RetrievalContextItem],
    ) -> GeneratedAnswer:
        """Generate answer using LLM with retrieved contexts.

        Args:
            query: User question
            contexts: Retrieved context items

        Returns:
            Generated answer with citations
        """
        selected_contexts = tuple(contexts[: self.max_context_items])

        if not selected_contexts:
            return GeneratedAnswer(
                answer="I could not find relevant context in this notebook.",
                used_context_ids=(),
                metadata={"strategy": "llm_generation", "no_context": True},
            )

        # Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(query, selected_contexts)

        # Generate answer
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm.generate(
            messages, temperature=self.temperature, max_tokens=self.max_tokens
        )

        # Extract citations from answer
        answer, used_context_ids = self._parse_citations(
            response.content, selected_contexts
        )

        return GeneratedAnswer(
            answer=answer,
            used_context_ids=tuple(used_context_ids),
            metadata={
                "strategy": "llm_generation",
                "model": response.model,
                "usage": response.usage,
                "total_contexts": len(selected_contexts),
                "used_contexts": len(used_context_ids),
            },
        )

    def _build_system_prompt(self) -> str:
        """Build system prompt for answer generation."""
        return """You are a helpful assistant that answers questions based on provided context.

Instructions:
1. Answer ONLY using information from the provided context passages
2. Cite your sources using [1], [2], etc. matching the passage numbers
3. If the context doesn't contain enough information, clearly state what is missing
4. Be concise but complete in your answer
5. Do not use external knowledge or make assumptions beyond the context
6. If you're unsure, say so rather than guessing"""

    def _build_user_prompt(
        self, query: str, contexts: Sequence[RetrievalContextItem]
    ) -> str:
        """Build user prompt with contexts."""
        # Format contexts with citation numbers
        context_parts = []
        for ctx in contexts:
            context_parts.append(f"[{ctx.citation_id}] {ctx.text}")

        context_text = "\n\n".join(context_parts)

        return f"""Context passages:

{context_text}

Question: {query}

Answer (remember to cite sources using [1], [2], etc.):"""

    def _parse_citations(
        self, answer: str, contexts: Sequence[RetrievalContextItem]
    ) -> tuple[str, list[str]]:
        """Extract citation IDs from answer text.

        Args:
            answer: Generated answer text
            contexts: Available context items

        Returns:
            Tuple of (answer text, list of used context_ids)
        """
        # Find all [1], [2], ... style citations in the answer
        citation_pattern = r"\[(\d+)\]"
        cited_numbers = set(re.findall(citation_pattern, answer))

        # Map citation numbers to context_ids
        citation_map = {ctx.citation_id: ctx.context_id for ctx in contexts}

        used_context_ids = [
            citation_map[cit_num]
            for cit_num in cited_numbers
            if cit_num in citation_map
        ]

        return answer, used_context_ids
