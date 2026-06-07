from fastapi.testclient import TestClient


def test_source_indexing_job_persists_nodes(persisted_client: TestClient) -> None:
    create_response = persisted_client.post(
        "/api/v1/sources",
        json={
            "source_id": "source-1",
            "notebook_id": "notebook-1",
            "filename": "guide.md",
            "media_type": "text/markdown",
            "text": (
                "# Introduction\n\n"
                "RAG systems combine retrieval and generation for grounded answers.\n\n"
                "## Evaluation\n\n"
                "Chunk inspection makes indexing quality visible."
            ),
        },
    )
    assert create_response.status_code == 201

    index_response = persisted_client.post("/api/v1/sources/source-1/index", json={})
    assert index_response.status_code == 200
    index_payload = index_response.json()
    assert index_payload["job"]["status"] == "succeeded"
    assert index_payload["job"]["node_count"] > 0

    job_id = index_payload["job"]["job_id"]
    job_response = persisted_client.get(f"/api/v1/indexing/jobs/{job_id}")
    assert job_response.status_code == 200
    assert job_response.json()["status"] == "succeeded"

    nodes_response = persisted_client.get("/api/v1/sources/source-1/nodes")
    assert nodes_response.status_code == 200
    nodes = nodes_response.json()
    assert len(nodes) == index_payload["job"]["node_count"]
    assert all(node["source_id"] == "source-1" for node in nodes)


def test_delete_source_index_removes_nodes(persisted_client: TestClient) -> None:
    persisted_client.post(
        "/api/v1/sources",
        json={
            "source_id": "source-2",
            "notebook_id": "notebook-1",
            "filename": "metrics.md",
            "media_type": "text/markdown",
            "blocks": [
                {"block_type": "heading", "text": "# Metrics", "page_no": 1},
                {
                    "block_type": "table",
                    "text": "| Metric | Value |\n| --- | --- |\n| Recall | 0.92 |",
                    "page_no": 1,
                },
            ],
        },
    )
    persisted_client.post("/api/v1/sources/source-2/index", json={})

    delete_response = persisted_client.delete("/api/v1/sources/source-2/index")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_count"] > 0

    nodes_response = persisted_client.get("/api/v1/sources/source-2/nodes")
    assert nodes_response.status_code == 200
    assert nodes_response.json() == []


def test_indexing_unknown_source_returns_404(persisted_client: TestClient) -> None:
    response = persisted_client.post("/api/v1/sources/missing-source/index", json={})

    assert response.status_code == 404
