from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

import anyio
from qdrant_client import QdrantClient, models

from ragmax.application.indexing.ports import VectorIndexRecord
from ragmax.domain.indexing.entities import IndexNode


class QdrantVectorIndexWriter:
    def __init__(self, *, client: QdrantClient, vector_size: int) -> None:
        self._client = client
        self._vector_size = vector_size

    async def upsert_nodes(
        self,
        *,
        collection_name: str,
        nodes: Sequence[IndexNode],
        embeddings: Sequence[Sequence[float]],
        embedding_model: str,
    ) -> tuple[VectorIndexRecord, ...]:
        if not nodes:
            return ()
        return await anyio.to_thread.run_sync(
            self._upsert_nodes_sync,
            collection_name,
            nodes,
            embeddings,
            embedding_model,
        )

    async def delete_source(
        self,
        *,
        collection_name: str,
        source_id: str,
    ) -> int:
        return await anyio.to_thread.run_sync(
            self._delete_source_sync,
            collection_name,
            source_id,
        )

    def _upsert_nodes_sync(
        self,
        collection_name: str,
        nodes: Sequence[IndexNode],
        embeddings: Sequence[Sequence[float]],
        embedding_model: str,
    ) -> tuple[VectorIndexRecord, ...]:
        self._ensure_collection(collection_name)
        vector_records = tuple(
            VectorIndexRecord(
                node_id=node.node_id,
                point_id=vector_point_id_for_node(node.node_id),
                collection_name=collection_name,
            )
            for node in nodes
        )
        points = [
            models.PointStruct(
                id=record.point_id,
                vector=list(vector),
                payload=_payload_from_node(
                    node,
                    collection_name=collection_name,
                    embedding_model=embedding_model,
                ),
            )
            for node, vector, record in zip(nodes, embeddings, vector_records, strict=True)
        ]
        self._client.upsert(collection_name=collection_name, points=points, wait=True)
        return vector_records

    def _delete_source_sync(self, collection_name: str, source_id: str) -> int:
        if not self._client.collection_exists(collection_name):
            return 0

        source_filter = _source_filter(source_id)
        count = self._client.count(
            collection_name=collection_name,
            count_filter=source_filter,
            exact=True,
        ).count
        self._client.delete(
            collection_name=collection_name,
            points_selector=source_filter,
            wait=True,
        )
        return int(count or 0)

    def _ensure_collection(self, collection_name: str) -> None:
        if self._client.collection_exists(collection_name):
            return
        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=self._vector_size,
                distance=models.Distance.COSINE,
            ),
        )


def _source_filter(source_id: str) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="source_id",
                match=models.MatchValue(value=source_id),
            )
        ]
    )


def vector_point_id_for_node(node_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, node_id))


def _payload_from_node(
    node: IndexNode,
    *,
    collection_name: str,
    embedding_model: str,
) -> dict[str, object]:
    return {
        "node_id": node.node_id,
        "source_id": node.source_id,
        "notebook_id": node.notebook_id,
        "modality": node.modality,
        "content_type": node.content_type,
        "page_start": node.page_start,
        "page_end": node.page_end,
        "section_path": list(node.section_path),
        "block_ids": list(node.block_ids),
        "parent_node_id": node.parent_node_id,
        "indexing_profile": node.indexing_profile,
        "parser_version": node.parser_version,
        "chunker_version": node.chunker_version,
        "embedding_model": embedding_model,
        "vector_collection": collection_name,
        "metadata": node.metadata,
        "text": node.text,
    }
