import pytest
from qdrant_client import QdrantClient, models

from ragmax.core.exceptions import ConfigurationError
from ragmax.domain.indexing.entities import IndexNode
from ragmax.infrastructure.qdrant.sparse_searcher import QdrantSparseBM25Searcher
from ragmax.infrastructure.qdrant.vector_index_writer import QdrantVectorIndexWriter
from ragmax.infrastructure.qdrant.vector_searcher import QdrantVectorSearcher


@pytest.mark.asyncio
async def test_qdrant_writer_creates_sparse_index_and_bm25_search_reads_payload_node_id() -> None:
    client = QdrantClient(":memory:")
    writer = QdrantVectorIndexWriter(client=client, vector_size=3, sparse_index_enabled=True)
    node = IndexNode(
        node_id="node-refund-1",
        source_id="source-1",
        notebook_id="notebook-1",
        text="退款审批需要财务 approval workflow",
        modality="text",
        content_type="paragraph",
    )

    await writer.upsert_nodes(
        collection_name="ragmax_text_nodes",
        nodes=(node,),
        embeddings=([0.2, 0.3, 0.4],),
        embedding_model="hash-test",
    )

    info = client.get_collection("ragmax_text_nodes")
    assert "text-sparse" in (info.config.params.sparse_vectors or {})

    vector_hits = await QdrantVectorSearcher(client=client).search(
        collection_names=("ragmax_text_nodes",),
        query_vector=[0.2, 0.3, 0.4],
        notebook_id="notebook-1",
        source_ids=(),
        content_types=(),
        limit=5,
    )
    assert vector_hits[0].node_id == "node-refund-1"

    searcher = QdrantSparseBM25Searcher(client=client)
    hits = await searcher.search(
        query="退款 approval",
        collection_names=("ragmax_text_nodes",),
        notebook_id="notebook-1",
        source_ids=(),
        content_types=(),
        limit=5,
    )

    assert hits
    assert hits[0].node_id == "node-refund-1"
    assert hits[0].collection_name == "ragmax_text_nodes"
    assert hits[0].payload["node_id"] == "node-refund-1"


@pytest.mark.asyncio
async def test_qdrant_writer_rejects_non_empty_dense_only_collection_when_sparse_enabled() -> None:
    client = QdrantClient(":memory:")
    client.create_collection(
        collection_name="ragmax_text_nodes",
        vectors_config=models.VectorParams(size=3, distance=models.Distance.COSINE),
    )
    client.upsert(
        collection_name="ragmax_text_nodes",
        points=[
            models.PointStruct(
                id="00000000-0000-0000-0000-000000000001",
                vector=[0.2, 0.3, 0.4],
                payload={"node_id": "existing-node"},
            )
        ],
        wait=True,
    )

    writer = QdrantVectorIndexWriter(client=client, vector_size=3, sparse_index_enabled=True)
    node = IndexNode(
        node_id="node-refund-1",
        source_id="source-1",
        notebook_id="notebook-1",
        text="退款审批",
        modality="text",
        content_type="paragraph",
    )

    with pytest.raises(ConfigurationError, match="does not define sparse vector"):
        await writer.upsert_nodes(
            collection_name="ragmax_text_nodes",
            nodes=(node,),
            embeddings=([0.2, 0.3, 0.4],),
            embedding_model="hash-test",
        )
