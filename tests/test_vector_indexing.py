import asyncio
from collections.abc import Iterator, Sequence

import pytest
from conftest import authenticate_test_client, db_session_override, seed_auth_user
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ragmax.api.dependencies import (
    create_indexing_service,
    get_indexing_service,
    get_source_storage,
)
from ragmax.application.indexing.ports import VectorIndexRecord
from ragmax.domain.indexing.entities import IndexNode
from ragmax.infrastructure.db.base import Base, import_models
from ragmax.infrastructure.db.repositories.indexing import SqlAlchemyIndexingUnitOfWork
from ragmax.infrastructure.db.session import get_db_session
from ragmax.infrastructure.indexing.embeddings.hash_embedding_provider import HashEmbeddingProvider
from ragmax.infrastructure.storage.local_source_storage import LocalSourceStorage
from ragmax.main import create_app


class FakeVectorIndexWriter:
    def __init__(self) -> None:
        self.upserts: list[dict[str, object]] = []
        self.deletes: list[dict[str, str]] = []
        self._last_point_count = 0

    async def upsert_nodes(
        self,
        *,
        collection_name: str,
        nodes: Sequence[IndexNode],
        embeddings: Sequence[Sequence[float]],
        embedding_model: str,
    ) -> tuple[VectorIndexRecord, ...]:
        self._last_point_count = len(nodes)
        self.upserts.append(
            {
                "collection_name": collection_name,
                "nodes": tuple(nodes),
                "embeddings": tuple(tuple(vector) for vector in embeddings),
                "embedding_model": embedding_model,
            }
        )
        return tuple(
            VectorIndexRecord(
                node_id=node.node_id,
                point_id=f"point-{index}",
                collection_name=collection_name,
            )
            for index, node in enumerate(nodes, start=1)
        )

    async def delete_source(self, *, collection_name: str, source_id: str) -> int:
        self.deletes.append({"collection_name": collection_name, "source_id": source_id})
        return self._last_point_count


@pytest.fixture
def vector_client(tmp_path) -> Iterator[tuple[TestClient, FakeVectorIndexWriter]]:
    import_models()
    database_url = f"sqlite+aiosqlite:///{tmp_path}/ragmax.db"
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    vector_writer = FakeVectorIndexWriter()

    async def setup_database() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def teardown_database() -> None:
        await engine.dispose()

    asyncio.run(setup_database())
    seed_auth_user(session_factory)

    app = create_app()
    app.dependency_overrides[get_db_session] = db_session_override(session_factory)
    app.dependency_overrides[get_indexing_service] = lambda: create_indexing_service(
        unit_of_work_factory=lambda: SqlAlchemyIndexingUnitOfWork(session_factory),
        embedding_provider=HashEmbeddingProvider(model_name="hash-test", dimension=8),
        vector_index_writer=vector_writer,
    )
    app.dependency_overrides[get_source_storage] = lambda: LocalSourceStorage(
        root_dir=tmp_path / "storage",
        max_upload_bytes=10 * 1024 * 1024,
    )

    with TestClient(app) as client:
        authenticate_test_client(client)
        yield client, vector_writer

    app.dependency_overrides.clear()
    asyncio.run(teardown_database())


def test_index_job_writes_vectors_and_persists_vector_metadata(
    vector_client: tuple[TestClient, FakeVectorIndexWriter],
) -> None:
    client, vector_writer = vector_client
    create_response = client.post(
        "/api/v1/sources",
        json={
            "source_id": "source-vector-1",
            "notebook_id": "notebook-1",
            "filename": "guide.md",
            "media_type": "text/markdown",
            "text": "# Intro\n\nVector indexing should persist metadata.",
        },
    )
    assert create_response.status_code == 201

    index_response = client.post("/api/v1/sources/source-vector-1/index", json={})

    assert index_response.status_code == 200
    payload = index_response.json()
    assert payload["job"]["vector_status"] == "succeeded"
    assert payload["job"]["summary"]["vector_index"]["embedding_model"] == "hash-test"
    assert payload["job"]["summary"]["vector_index"]["node_count"] > 0
    assert vector_writer.upserts
    assert vector_writer.upserts[0]["embedding_model"] == "hash-test"
    vectorized_nodes = tuple(vector_writer.upserts[0]["nodes"])
    assert all(node.content_type != "section" for node in vectorized_nodes)

    nodes_response = client.get("/api/v1/sources/source-vector-1/nodes")
    assert nodes_response.status_code == 200
    nodes = nodes_response.json()
    assert nodes
    parent_nodes = [node for node in nodes if node["content_type"] == "section"]
    vectorized_node_ids = {node.node_id for node in vectorized_nodes}
    assert parent_nodes
    assert all(node["embedding_model"] is None for node in parent_nodes)
    assert all("vector_point_id" not in node["metadata"] for node in parent_nodes)
    assert all(
        node["embedding_model"] == "hash-test"
        for node in nodes
        if node["node_id"] in vectorized_node_ids
    )
    assert all(
        node["metadata"]["vector_point_id"].startswith("point-")
        for node in nodes
        if node["node_id"] in vectorized_node_ids
    )

    artifacts_response = client.get(
        f"/api/v1/indexing/jobs/{payload['job']['job_id']}/artifacts"
    )
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()
    assert set(artifacts["vectorized_node_ids"]) == vectorized_node_ids
    assert artifacts["metrics"]["vectorized_count"] == len(vectorized_nodes)

    delete_response = client.delete("/api/v1/sources/source-vector-1/index")
    assert delete_response.status_code == 200
    assert delete_response.json()["vector_deleted_count"] == len(vectorized_nodes)
    assert vector_writer.deletes == [
        {"collection_name": "ragmax_text_nodes", "source_id": "source-vector-1"}
    ]
