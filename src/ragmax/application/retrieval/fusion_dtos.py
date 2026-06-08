"""DTOs for search result fusion."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BM25SearchHit:
    """Result from BM25 lexical search."""

    node_id: str
    score: float
    collection_name: str = ""
    matched_terms: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FusedSearchHit:
    """Fused result from multiple search strategies."""

    node_id: str
    fused_score: float
    vector_score: float | None = None
    bm25_score: float | None = None
    vector_rank: int | None = None
    bm25_rank: int | None = None
    collection_name: str = ""
    matched_terms: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)
