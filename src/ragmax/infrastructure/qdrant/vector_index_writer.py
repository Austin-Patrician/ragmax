from collections.abc import Sequence
from uuid import NAMESPACE_URL, uuid5

import anyio
from qdrant_client import QdrantClient, models

from ragmax.application.indexing.ports import VectorIndexRecord
from ragmax.core.exceptions import ConfigurationError
from ragmax.domain.indexing.entities import IndexNode
from ragmax.infrastructure.qdrant.sparse_encoder import SPARSE_VECTOR_NAME, SparseTextEncoder


class QdrantVectorIndexWriter:
    def __init__(
        self,
        *,
        client: QdrantClient,
        vector_size: int,
        sparse_index_enabled: bool = True,
        sparse_encoder: SparseTextEncoder | None = None,
    ) -> None:
        self._client = client
        self._vector_size = vector_size
        self._sparse_index_enabled = sparse_index_enabled
        self._sparse_encoder = sparse_encoder or SparseTextEncoder()

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
        points: list[models.PointStruct] = []
        for node, vector, record in zip(nodes, embeddings, vector_records, strict=True):
            sparse_vector = None
            sparse_terms: tuple[str, ...] = ()
            if self._sparse_index_enabled:
                sparse_vector, sparse_terms = self._sparse_encoder.encode(node.text)

            points.append(
                models.PointStruct(
                    id=record.point_id,
                    vector=_point_vector(
                        dense_vector=vector,
                        sparse_vector=sparse_vector,
                    ),
                    payload=_payload_from_node(
                        node,
                        collection_name=collection_name,
                        embedding_model=embedding_model,
                        sparse_terms_count=len(sparse_terms)
                        if self._sparse_index_enabled
                        else None,
                    ),
                )
            )
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
            if self._sparse_index_enabled:
                self._ensure_sparse_vector(collection_name)
            return
        self._create_collection(collection_name)

    def _create_collection(self, collection_name: str) -> None:
        sparse_vectors_config = None
        if self._sparse_index_enabled:
            sparse_vectors_config = {
                SPARSE_VECTOR_NAME: models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                    index=models.SparseIndexParams(on_disk=False),
                )
            }
        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=self._vector_size,
                distance=models.Distance.COSINE,
            ),
            sparse_vectors_config=sparse_vectors_config,
        )

    def _ensure_sparse_vector(self, collection_name: str) -> None:
        info = self._client.get_collection(collection_name)
        sparse_vectors = info.config.params.sparse_vectors or {}
        if SPARSE_VECTOR_NAME in sparse_vectors:
            return

        point_count = int(info.points_count or 0)
        if point_count == 0:
            self._client.delete_collection(collection_name)
            self._create_collection(collection_name)
            return

        raise ConfigurationError(
            f"Qdrant collection '{collection_name}' does not define sparse vector "
            f"'{SPARSE_VECTOR_NAME}' and contains {point_count} points. Delete or rebuild "
            "the collection, then re-run indexing to enable BM25 sparse retrieval."
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
    sparse_terms_count: int | None = None,
) -> dict[str, object]:
    metadata = dict(node.metadata)
    if sparse_terms_count is not None:
        metadata.update(
            {
                "sparse_indexed": True,
                "sparse_terms_count": sparse_terms_count,
                "sparse_vector_name": SPARSE_VECTOR_NAME,
            }
        )

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
        "node_role": _node_role(node),
        "indexing_profile": node.indexing_profile,
        "parser_version": node.parser_version,
        "chunker_version": node.chunker_version,
        "embedding_model": embedding_model,
        "vector_collection": collection_name,
        "metadata": metadata,
        "text": node.text,
    }


def _node_role(node: IndexNode) -> str:
    if node.parent_node_id:
        return "child"
    if node.content_type == "section":
        return "parent"
    return "leaf"


def _point_vector(
    *,
    dense_vector: Sequence[float],
    sparse_vector: models.SparseVector | None,
) -> list[float] | dict[str, list[float] | models.SparseVector]:
    if sparse_vector is None:
        return list(dense_vector)
    return {"": list(dense_vector), SPARSE_VECTOR_NAME: sparse_vector}
