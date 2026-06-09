from fastapi.testclient import TestClient


def test_indexing_pipeline_executes_stage_and_reads_artifact(
    persisted_client: TestClient,
) -> None:
    persisted_client.post(
        "/api/v1/sources",
        json={
            "source_id": "pipeline-source-1",
            "notebook_id": "notebook-1",
            "filename": "guide.md",
            "media_type": "text/markdown",
            "text": "# Intro\n\nIndexing stages should expose artifacts.",
        },
    )

    create_response = persisted_client.post(
        "/api/v1/sources/pipeline-source-1/index/runs",
        json={},
    )
    assert create_response.status_code == 200
    run_payload = create_response.json()
    run_id = run_payload["run"]["run_id"]
    assert [stage["stage_name"] for stage in run_payload["stages"]] == [
        "source",
        "parse_blocks",
        "analyze_profile",
        "chunk_nodes",
        "quality_enrich",
        "vectorize",
    ]

    source_response = persisted_client.post(
        f"/api/v1/indexing/runs/{run_id}/stages/source/execute"
    )
    assert source_response.status_code == 200
    assert source_response.json()["stage_run"]["status"] == "succeeded"

    parse_response = persisted_client.post(
        f"/api/v1/indexing/runs/{run_id}/stages/parse_blocks/execute"
    )
    assert parse_response.status_code == 200
    manifests = parse_response.json()["manifests"]
    blocks_manifest = next(
        manifest for manifest in manifests if manifest["artifact_type"] == "blocks"
    )
    assert blocks_manifest["record_count"] > 0
    assert blocks_manifest["storage_uri"].endswith("blocks.jsonl")

    artifact_response = persisted_client.get(
        f"/api/v1/indexing/artifacts/{blocks_manifest['artifact_id']}?offset=0&limit=1"
    )
    assert artifact_response.status_code == 200
    artifact_payload = artifact_response.json()
    assert len(artifact_payload["data"]) == 1
    assert artifact_payload["data"][0]["block_type"] in {"heading", "text"}


def test_indexing_pipeline_execute_all_persists_latest_nodes(
    persisted_client: TestClient,
) -> None:
    persisted_client.post(
        "/api/v1/sources",
        json={
            "source_id": "pipeline-source-2",
            "notebook_id": "notebook-1",
            "filename": "guide.md",
            "media_type": "text/markdown",
            "text": (
                "# Intro\n\n"
                "Indexing stages should be executable end to end.\n\n"
                "## Quality\n\n"
                "Chunks need useful metadata."
            ),
        },
    )
    create_response = persisted_client.post(
        "/api/v1/sources/pipeline-source-2/index/runs",
        json={},
    )
    run_id = create_response.json()["run"]["run_id"]

    execute_response = persisted_client.post(f"/api/v1/indexing/runs/{run_id}/execute")
    assert execute_response.status_code == 200, execute_response.text
    payload = execute_response.json()
    assert payload["run"]["status"] == "succeeded"
    assert all(stage["status"] == "succeeded" for stage in payload["stages"])
    assert payload["run"]["summary"]["job_id"].startswith("job_")

    nodes_response = persisted_client.get("/api/v1/sources/pipeline-source-2/nodes")
    assert nodes_response.status_code == 200
    assert len(nodes_response.json()) > 0


def test_indexing_pipeline_rejects_stage_without_dependency(
    persisted_client: TestClient,
) -> None:
    persisted_client.post(
        "/api/v1/sources",
        json={
            "source_id": "pipeline-source-3",
            "notebook_id": "notebook-1",
            "filename": "guide.md",
            "media_type": "text/markdown",
            "text": "# Intro\n\nDependencies should be enforced.",
        },
    )
    create_response = persisted_client.post(
        "/api/v1/sources/pipeline-source-3/index/runs",
        json={},
    )
    run_id = create_response.json()["run"]["run_id"]

    response = persisted_client.post(
        f"/api/v1/indexing/runs/{run_id}/stages/chunk_nodes/execute"
    )
    assert response.status_code == 400
    assert "requires fresh successful" in response.json()["detail"]
