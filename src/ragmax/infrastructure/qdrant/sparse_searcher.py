"""BM25 search using Qdrant sparse vectors."""

from collections.abc import Sequence
from typing import Any

import anyio
from qdrant_client import QdrantClient, models

from ragmax.application.retrieval.fusion_dtos import BM25SearchHit
from ragmax.core.exceptions import ConfigurationError
from ragmax.infrastructure.qdrant.sparse_encoder import SPARSE_VECTOR_NAME, SparseTextEncoder


class QdrantSparseBM25Searcher:
    """BM25 search implementation using Qdrant's native sparse vector support.

    This implementation uses Qdrant v1.10+ sparse vectors to perform BM25-style
    lexical search without requiring a separate full-text search infrastructure.
    """

    def __init__(
        self,
        *,
        client: QdrantClient,
        sparse_encoder: SparseTextEncoder | None = None,
    ) -> None:
        """Initialize sparse BM25 searcher.

        Args:
            client: Async Qdrant client
        """
        self._client = client
        self._sparse_encoder = sparse_encoder or SparseTextEncoder()

    async def search(
        self,
        *,
        query: str,
        collection_names: Sequence[str],
        notebook_id: str,
        source_ids: Sequence[str],
        content_types: Sequence[str],
        limit: int,
    ) -> tuple[BM25SearchHit, ...]:
        """Execute BM25 search using sparse vectors.

        Args:
            query: Search query text
            collection_names: Qdrant collections to search
            notebook_id: Notebook ID filter
            source_ids: Optional source ID filters
            content_types: Optional content type filters
            limit: Maximum number of results

        Returns:
            BM25 search hits sorted by score (descending)
        """
        return await anyio.to_thread.run_sync(
            self._search_sync,
            query,
            collection_names,
            notebook_id,
            source_ids,
            content_types,
            limit,
        )

    def _search_sync(
        self,
        query: str,
        collection_names: Sequence[str],
        notebook_id: str,
        source_ids: Sequence[str],
        content_types: Sequence[str],
        limit: int,
    ) -> tuple[BM25SearchHit, ...]:
        sparse_query, matched_terms = self._sparse_encoder.encode(query)
        if not sparse_query.indices:
            return ()

        filter_conditions: list[models.FieldCondition] = [
            models.FieldCondition(
                key="notebook_id",
                match=models.MatchValue(value=notebook_id),
            )
        ]

        if source_ids:
            filter_conditions.append(
                models.FieldCondition(
                    key="source_id",
                    match=models.MatchAny(any=list(source_ids)),
                )
            )

        if content_types:
            filter_conditions.append(
                models.FieldCondition(
                    key="content_type",
                    match=models.MatchAny(any=list(content_types)),
                )
            )

        # Search across all collections
        all_hits: list[BM25SearchHit] = []

        for collection_name in collection_names:
            if not self._client.collection_exists(collection_name):
                continue
            self._ensure_sparse_vector(collection_name)
            response = self._client.query_points(
                collection_name=collection_name,
                query=sparse_query,
                using=SPARSE_VECTOR_NAME,
                query_filter=models.Filter(must=filter_conditions),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            for result in _points_from_response(response):
                payload = dict(getattr(result, "payload", None) or {})
                node_id = payload.get("node_id")
                if not node_id:
                    continue
                all_hits.append(
                    BM25SearchHit(
                        node_id=str(node_id),
                        score=float(getattr(result, "score", 0.0)),
                        collection_name=collection_name,
                        matched_terms=matched_terms,
                        payload=payload,
                    )
                )

        # Sort by score descending and limit
        all_hits.sort(key=lambda x: x.score, reverse=True)
        return tuple(all_hits[:limit])

    def _ensure_sparse_vector(self, collection_name: str) -> None:
        info = self._client.get_collection(collection_name)
        sparse_vectors = info.config.params.sparse_vectors or {}
        if SPARSE_VECTOR_NAME in sparse_vectors:
            return
        raise ConfigurationError(
            f"Qdrant collection '{collection_name}' does not define sparse vector "
            f"'{SPARSE_VECTOR_NAME}'. Rebuild the collection and re-run indexing before "
            "enabling BM25 retrieval."
        )


def _points_from_response(response: Any) -> list[Any]:
    points = getattr(response, "points", None)
    if points is None and isinstance(response, list):
        points = response
    return list(points or [])
