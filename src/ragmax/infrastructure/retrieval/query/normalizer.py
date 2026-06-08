"""Query normalization implementations."""

import re

from ragmax.application.retrieval.query_dtos import NormalizedQuery


class BasicQueryNormalizer:
    """Basic query normalizer that cleans whitespace and special characters."""

    def __init__(self) -> None:
        self._whitespace_pattern = re.compile(r"\s+")

    def normalize(self, query: str) -> NormalizedQuery:
        """Normalize query by cleaning whitespace."""
        # Strip leading/trailing whitespace
        stripped = query.strip()

        # Collapse multiple whitespace into single space
        normalized = self._whitespace_pattern.sub(" ", stripped)

        return NormalizedQuery(
            original=query,
            normalized=normalized,
            language=None,  # Language detection not implemented yet
        )
