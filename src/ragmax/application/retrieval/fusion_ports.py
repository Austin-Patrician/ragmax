"""Ports for search result fusion."""

from collections.abc import Sequence
from typing import Protocol

from ragmax.application.retrieval.fusion_dtos import BM25SearchHit, FusedSearchHit
from ragmax.application.retrieval.ports import VectorSearchHit


class BM25Searcher(Protocol):
    """Interface for BM25 lexical search."""

    async def search(
        self,
        *,
        query: str,
        collection_names: Sequence[str],
        source_ids: Sequence[str],
        content_types: Sequence[str],
        limit: int,
    ) -> tuple[BM25SearchHit, ...]:
        """Execute BM25 lexical search."""
        ...


class SearchFuser(Protocol):
    """Interface for fusing multiple search results."""

    def fuse(
        self,
        *,
        vector_hits: Sequence[VectorSearchHit],
        bm25_hits: Sequence[BM25SearchHit],
        top_k: int,
    ) -> tuple[FusedSearchHit, ...]:
        """Fuse vector and BM25 search results."""
        ...
