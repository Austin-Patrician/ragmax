import asyncio
from collections.abc import Iterator, Sequence

import pytest
from conftest import authenticate_test_client, db_session_override, seed_auth_user
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ragmax.api.dependencies import (
    create_indexing_service,
    create_retrieval_service,
    get_indexing_service,
    get_retrieval_service,
    get_source_storage,
)
from ragmax.application.retrieval.ports import VectorSearchHit
from ragmax.infrastructure.db.base import Base, import_models
from ragmax.infrastructure.db.repositories.indexing import SqlAlchemyIndexingUnitOfWork
from ragmax.infrastructure.db.session import get_db_session
from ragmax.infrastructure.indexing.embeddings.hash_embedding_provider import HashEmbeddingProvider
from ragmax.infrastructure.storage.local_source_storage import LocalSourceStorage
from ragmax.main import create_app


class FakeVectorSearcher:
    def __init__(self) -> None:
        self.hits: tuple[VectorSearchHit, ...] = ()
        self.calls: list[dict[str, object]] = []

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
        self.calls.append(
            {
                "collection_names": tuple(collection_names),
                "query_vector": tuple(query_vector),
                "notebook_id": notebook_id,
                "source_ids": tuple(source_ids),
                "content_types": tuple(content_types),
                "limit": limit,
                "score_threshold": score_threshold,
            }
        )
        return self.hits


@pytest.fixture
def retrieval_client(tmp_path) -> Iterator[tuple[TestClient, FakeVectorSearcher]]:
    import_models()
    database_url = f"sqlite+aiosqlite:///{tmp_path}/ragmax.db"
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    vector_searcher = FakeVectorSearcher()
    embedding_provider = HashEmbeddingProvider(model_name="hash-test", dimension=8)

    async def setup_database() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def teardown_database() -> None:
        await engine.dispose()

    asyncio.run(setup_database())
    seed_auth_user(session_factory)

    app = create_app()
    app.dependency_overrides[get_db_session] = db_session_override(session_factory)
    source_storage = LocalSourceStorage(
        root_dir=tmp_path / "storage",
        max_upload_bytes=10 * 1024 * 1024,
    )
    app.dependency_overrides[get_indexing_service] = lambda: create_indexing_service(
        unit_of_work_factory=lambda: SqlAlchemyIndexingUnitOfWork(session_factory),
        source_storage=source_storage,
    )
    app.dependency_overrides[get_retrieval_service] = lambda: create_retrieval_service(
        unit_of_work_factory=lambda: SqlAlchemyIndexingUnitOfWork(session_factory),
        embedding_provider=embedding_provider,
        vector_searcher=vector_searcher,
    )
    app.dependency_overrides[get_source_storage] = lambda: source_storage

    with TestClient(app) as client:
        authenticate_test_client(client)
        yield client, vector_searcher

    app.dependency_overrides.clear()
    asyncio.run(teardown_database())


def test_retrieval_disabled_returns_configuration_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/retrieval/search",
        json={"query": "cash flow", "notebook_id": "notebook-1"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Retrieval is not configured."


def test_retrieval_answer_disabled_returns_configuration_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/retrieval/answer",
        json={"query": "cash flow", "notebook_id": "notebook-1"},
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Retrieval is not configured."


def test_retrieval_search_hydrates_nodes_and_passes_filters(
    retrieval_client: tuple[TestClient, FakeVectorSearcher],
) -> None:
    client, vector_searcher = retrieval_client
    create_response = client.post(
        "/api/v1/sources",
        json={
            "source_id": "source-retrieval-1",
            "notebook_id": "notebook-1",
            "filename": "guide.md",
            "media_type": "text/markdown",
            "text": "# Cash Flow\n\nOperating cash flow declined in the second quarter.",
        },
    )
    assert create_response.status_code == 201

    index_response = client.post("/api/v1/sources/source-retrieval-1/index", json={})
    assert index_response.status_code == 200
    nodes_response = client.get("/api/v1/sources/source-retrieval-1/nodes")
    nodes = nodes_response.json()
    assert nodes

    vector_searcher.hits = (
        VectorSearchHit(
            node_id=nodes[0]["node_id"],
            score=0.91,
            collection_name="ragmax_text_nodes",
            payload={"node_id": nodes[0]["node_id"]},
        ),
        VectorSearchHit(
            node_id="missing-node",
            score=0.88,
            collection_name="ragmax_text_nodes",
            payload={"node_id": "missing-node"},
        ),
    )

    response = client.post(
        "/api/v1/retrieval/search",
        json={
            "query": "What happened to cash flow?",
            "notebook_id": "notebook-1",
            "top_k": 5,
            "source_ids": ["source-retrieval-1"],
            "content_types": ["paragraph"],
            "score_threshold": 0.2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["node_id"] == nodes[0]["node_id"]
    assert payload["results"][0]["score"] == 0.91
    assert payload["results"][0]["citation"]["filename"] == "guide.md"

    call = vector_searcher.calls[-1]
    assert call["collection_names"] == ("ragmax_text_nodes",)
    assert call["notebook_id"] == "notebook-1"
    assert call["source_ids"] == ("source-retrieval-1",)
    assert call["content_types"] == ("paragraph",)
    assert call["limit"] == 5
    assert call["score_threshold"] == 0.2
    assert len(call["query_vector"]) == 8


def test_retrieval_answer_reranks_and_returns_context_ready_items(
    retrieval_client: tuple[TestClient, FakeVectorSearcher],
) -> None:
    client, vector_searcher = retrieval_client
    related_node = _create_indexed_source(
        client,
        source_id="source-answer-related",
        text="The refund policy requires approval from finance before the payout is released.",
        filename="refund-policy.md",
    )
    unrelated_node = _create_indexed_source(
        client,
        source_id="source-answer-unrelated",
        text="Inventory forecasts were updated after the warehouse count changed.",
        filename="inventory.md",
    )

    vector_searcher.hits = (
        VectorSearchHit(
            node_id="missing-node",
            score=0.99,
            collection_name="ragmax_text_nodes",
            payload={"node_id": "missing-node"},
        ),
        VectorSearchHit(
            node_id=unrelated_node["node_id"],
            score=0.8,
            collection_name="ragmax_text_nodes",
            payload={"node_id": unrelated_node["node_id"]},
        ),
        VectorSearchHit(
            node_id=related_node["node_id"],
            score=0.7,
            collection_name="ragmax_text_nodes",
            payload={"node_id": related_node["node_id"]},
        ),
    )

    response = client.post(
        "/api/v1/retrieval/answer",
        json={
            "query": "refund policy approval",
            "notebook_id": "notebook-1",
            "retrieval_top_k": 3,
            "rerank_top_k": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["retrieval_count"] == 2
    assert payload["rerank_count"] == 2
    assert payload["reranker"] == "score_keyword_reranker:v1"
    assert payload["answer_generator"] == "extractive_answer_generator:v1"
    assert "[1]" in payload["answer"]

    contexts = payload["contexts"]
    assert [context["node_id"] for context in contexts] == [
        related_node["node_id"],
        unrelated_node["node_id"],
    ]
    assert contexts[0]["citation_id"] == "1"
    assert contexts[0]["citation"]["filename"] == "refund-policy.md"
    assert contexts[0]["vector_score"] == 0.7
    assert contexts[0]["rerank_score"] > contexts[1]["rerank_score"]
    assert contexts[0]["metadata"]["retrieval"]["rerank_metadata"]["matched_terms"] == [
        "approval",
        "policy",
        "refund",
    ]

    citations = payload["citations"]
    assert citations[0]["context_id"] == contexts[0]["context_id"]
    assert citations[0]["node_id"] == related_node["node_id"]

    call = vector_searcher.calls[-1]
    assert call["limit"] == 3


def test_retrieval_answer_expands_child_hit_to_parent_context(
    retrieval_client: tuple[TestClient, FakeVectorSearcher],
) -> None:
    client, vector_searcher = retrieval_client
    create_response = client.post(
        "/api/v1/sources",
        json={
            "source_id": "source-parent-context",
            "notebook_id": "notebook-1",
            "filename": "parent-guide.md",
            "media_type": "text/markdown",
            "text": (
                "# Refund Policy\n\n"
                "## Approval\n\n"
                "Refund approval requires finance review before payout is released."
            ),
        },
    )
    assert create_response.status_code == 201

    index_response = client.post("/api/v1/sources/source-parent-context/index", json={})
    assert index_response.status_code == 200
    nodes_response = client.get("/api/v1/sources/source-parent-context/nodes")
    assert nodes_response.status_code == 200
    nodes = nodes_response.json()
    child = next(node for node in nodes if node["parent_node_id"])
    parent = next(node for node in nodes if node["node_id"] == child["parent_node_id"])

    vector_searcher.hits = (
        VectorSearchHit(
            node_id=child["node_id"],
            score=0.91,
            collection_name="ragmax_text_nodes",
            payload={"node_id": child["node_id"], "node_role": "child"},
        ),
    )

    response = client.post(
        "/api/v1/retrieval/answer",
        json={
            "query": "refund approval finance",
            "notebook_id": "notebook-1",
        },
    )

    assert response.status_code == 200
    context = response.json()["contexts"][0]
    assert context["node_id"] == parent["node_id"]
    assert context["content_type"] == "section"
    assert context["metadata"]["retrieval"]["matched_node_id"] == child["node_id"]
    assert context["metadata"]["retrieval"]["context_node_id"] == parent["node_id"]
    assert context["metadata"]["retrieval"]["expanded_from_parent"] is True


def _create_indexed_source(
    client: TestClient,
    *,
    source_id: str,
    text: str,
    filename: str,
) -> dict[str, object]:
    create_response = client.post(
        "/api/v1/sources",
        json={
            "source_id": source_id,
            "notebook_id": "notebook-1",
            "filename": filename,
            "media_type": "text/markdown",
            "text": text,
        },
    )
    assert create_response.status_code == 201

    index_response = client.post(f"/api/v1/sources/{source_id}/index", json={})
    assert index_response.status_code == 200
    nodes_response = client.get(f"/api/v1/sources/{source_id}/nodes")
    assert nodes_response.status_code == 200
    nodes = nodes_response.json()
    assert nodes
    return nodes[0]
