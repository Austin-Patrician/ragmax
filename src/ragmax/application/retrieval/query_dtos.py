"""DTOs for query processing."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NormalizedQuery:
    """Normalized query with metadata."""

    original: str
    normalized: str
    language: str | None = None


@dataclass(frozen=True)
class TransformedQuery:
    """Transformed query with variants."""

    original: str
    variants: tuple[str, ...]  # Query variants for multi-query search
    strategy: str  # "original" | "hyde" | "multi_query"
    metadata: dict[str, Any] | None = None
