"""Query transformation implementations."""

from collections.abc import Sequence

from ragmax.application.retrieval.query_dtos import NormalizedQuery, TransformedQuery


class OriginalQueryTransformer:
    """Pass-through transformer that returns the original query."""

    async def transform(
        self,
        query: NormalizedQuery,
        strategy: str = "original",
    ) -> TransformedQuery:
        """Return the original query without transformation."""
        return TransformedQuery(
            original=query.normalized,
            variants=(query.normalized,),
            strategy="original",
            metadata=None,
        )


class HyDETransformer:
    """HyDE (Hypothetical Document Embeddings) transformer.

    Generates a synthetic hypothetical document that would answer the query,
    then uses that for retrieval instead of the raw query.
    """

    def __init__(self, llm_client: "LLMClient") -> None:  # noqa: F821
        """Initialize with an LLM client.

        Args:
            llm_client: Client for generating hypothetical documents
        """
        self.llm = llm_client

    async def transform(
        self,
        query: NormalizedQuery,
        strategy: str = "hyde",
    ) -> TransformedQuery:
        """Generate a hypothetical document for the query."""
        from ragmax.infrastructure.llm.client import LLMMessage

        system_prompt = (
            "You are an expert assistant. "
            "Write a detailed passage that would perfectly answer the following question. "
            "The passage should be factual and comprehensive."
        )

        user_prompt = f"Question: {query.normalized}\n\nPassage:"

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm.generate(messages, temperature=0.3, max_tokens=500)

        return TransformedQuery(
            original=query.normalized,
            variants=(response.content.strip(),),
            strategy="hyde",
            metadata={
                "model": response.model,
                "usage": response.usage,
            },
        )


class MultiQueryTransformer:
    """Multi-query transformer that generates multiple query variants."""

    def __init__(self, llm_client: "LLMClient", num_variants: int = 3) -> None:  # noqa: F821
        """Initialize with an LLM client.

        Args:
            llm_client: Client for generating query variants
            num_variants: Number of query variants to generate (default: 3)
        """
        self.llm = llm_client
        self.num_variants = max(1, num_variants)

    async def transform(
        self,
        query: NormalizedQuery,
        strategy: str = "multi_query",
    ) -> TransformedQuery:
        """Generate multiple variants of the query."""
        from ragmax.infrastructure.llm.client import LLMMessage

        system_prompt = (
            "You are an expert at rephrasing questions. "
            f"Generate {self.num_variants} different ways to ask the same question. "
            "Each variant should capture the same intent but use different wording. "
            f"Return exactly {self.num_variants} variants, one per line, numbered."
        )

        user_prompt = f"Original question: {query.normalized}\n\nVariants:"

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response = await self.llm.generate(messages, temperature=0.5, max_tokens=300)

        # Parse variants from response (format: "1. Variant 1\n2. Variant 2\n...")
        variants = self._parse_variants(response.content)

        # Include original query as first variant
        all_variants = (query.normalized,) + variants

        return TransformedQuery(
            original=query.normalized,
            variants=all_variants,
            strategy="multi_query",
            metadata={
                "model": response.model,
                "usage": response.usage,
                "generated_count": len(variants),
            },
        )

    def _parse_variants(self, content: str) -> tuple[str, ...]:
        """Parse numbered variants from LLM response."""
        lines = content.strip().split("\n")
        variants: list[str] = []

        for line in lines:
            # Remove numbering (e.g., "1. ", "2) ", etc.)
            cleaned = line.strip()
            if cleaned:
                # Remove common numbering patterns
                import re

                cleaned = re.sub(r"^\d+[\.\)]\s*", "", cleaned)
                if cleaned:
                    variants.append(cleaned)

        return tuple(variants[: self.num_variants])


def create_query_transformer(
    strategy: str,
    llm_client: "LLMClient | None" = None,  # noqa: F821
    num_variants: int = 3,
) -> "OriginalQueryTransformer | HyDETransformer | MultiQueryTransformer":
    """Factory function to create appropriate query transformer.

    Args:
        strategy: Transformation strategy ("original", "hyde", "multi_query")
        llm_client: LLM client (required for "hyde" and "multi_query")
        num_variants: Number of variants for multi_query strategy

    Returns:
        Appropriate QueryTransformer implementation

    Raises:
        ValueError: If strategy requires LLM client but none provided
    """
    if strategy == "original":
        return OriginalQueryTransformer()

    if llm_client is None:
        raise ValueError(f"Strategy '{strategy}' requires an LLM client")

    if strategy == "hyde":
        return HyDETransformer(llm_client)

    if strategy == "multi_query":
        return MultiQueryTransformer(llm_client, num_variants)

    raise ValueError(f"Unknown query transformation strategy: {strategy}")
