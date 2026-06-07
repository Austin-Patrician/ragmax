from collections.abc import Sequence
from typing import Any

import anyio
from qdrant_client import QdrantClient, models

from ragmax.application.retrieval.ports import VectorSearchHit


class QdrantVectorSearcher:
    def __init__(self, *, client: QdrantClient) -> None:
        self._client = client

    async def search(
        self,
        *,
        collection_names: Sequence[str],
        query_vector: Sequence[float],
        notebook_id: str,
        source_ids: Sequence[str],
        content_types: Sequence[str],
        limit: int,
        score_threshold: float | None = None,
    ) -> tuple[VectorSearchHit, ...]:
        return await anyio.to_thread.run_sync(
            self._search_sync,
            collection_names,
            query_vector,
            notebook_id,
            source_ids,
            content_types,
            limit,
            score_threshold,
        )

    def _search_sync(
        self,
        collection_names: Sequence[str],
        query_vector: Sequence[float],
        notebook_id: str,
        source_ids: Sequence[str],
        content_types: Sequence[str],
        limit: int,
        score_threshold: float | None,
    ) -> tuple[VectorSearchHit, ...]:
        hits: list[VectorSearchHit] = []
        query_filter = _query_filter(
            notebook_id=notebook_id,
            source_ids=source_ids,
            content_types=content_types,
        )
        for collection_name in collection_names:
            if not self._client.collection_exists(collection_name):
                continue
            response = self._client.query_points(
                collection_name=collection_name,
                query=list(query_vector),
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
                with_vectors=False,
                score_threshold=score_threshold,
            )
            hits.extend(_hits_from_response(response, collection_name))

        return tuple(sorted(hits, key=lambda hit: hit.score, reverse=True)[:limit])


def _query_filter(
    *,
    notebook_id: str,
    source_ids: Sequence[str],
    content_types: Sequence[str],
) -> models.Filter:
    must: list[models.Condition] = [
        models.FieldCondition(
            key="notebook_id",
            match=models.MatchValue(value=notebook_id),
        )
    ]
    if source_ids:
        must.append(
            models.FieldCondition(
                key="source_id",
                match=models.MatchAny(any=list(source_ids)),
            )
        )
    if content_types:
        must.append(
            models.FieldCondition(
                key="content_type",
                match=models.MatchAny(any=list(content_types)),
            )
        )
    return models.Filter(must=must)


def _hits_from_response(response: Any, collection_name: str) -> list[VectorSearchHit]:
    points = getattr(response, "points", None)
    if points is None and isinstance(response, list):
        points = response
    if points is None:
        return []

    hits: list[VectorSearchHit] = []
    for point in points:
        payload = dict(getattr(point, "payload", None) or {})
        node_id = payload.get("node_id")
        if not node_id:
            continue
        hits.append(
            VectorSearchHit(
                node_id=str(node_id),
                score=float(getattr(point, "score", 0.0)),
                collection_name=collection_name,
                payload=payload,
            )
        )
    return hits
