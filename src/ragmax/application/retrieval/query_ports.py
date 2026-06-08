"""Ports for query processing."""

from typing import Protocol

from ragmax.application.retrieval.query_dtos import NormalizedQuery, TransformedQuery


class QueryNormalizer(Protocol):
    """Interface for query normalization."""

    def normalize(self, query: str) -> NormalizedQuery:
        """Normalize a raw query string."""
        ...


class QueryTransformer(Protocol):
    """Interface for query transformation."""

    async def transform(
        self,
        query: NormalizedQuery,
        strategy: str = "original",
    ) -> TransformedQuery:
        """Transform a normalized query using the specified strategy."""
        ...
