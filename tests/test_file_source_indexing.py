from fastapi.testclient import TestClient


def test_indexing_parsers_lists_user_visible_parsers(client: TestClient) -> None:
    response = client.get("/api/v1/indexing/parsers")

    assert response.status_code == 200
    parsers = response.json()
    parser_names = {parser["name"] for parser in parsers}
    assert parser_names == {"simple_directory_reader", "llamaparse", "mineru"}
    assert "inline_content_parser" not in parser_names
    default_parsers = [parser["name"] for parser in parsers if parser["is_default"]]
    assert len(default_parsers) <= 1
    assert set(default_parsers) <= parser_names


def test_uploaded_text_source_indexes_with_default_simple_directory_reader(
    persisted_client: TestClient,
) -> None:
    upload_response = persisted_client.post(
        "/api/v1/sources/upload",
        data={
            "source_id": "uploaded-source-1",
            "notebook_id": "notebook-1",
            "metadata": '{"title": "Guide"}',
        },
        files={
            "file": (
                "guide.txt",
                b"# Introduction\n\nRAG indexing starts with reliable parsing.",
                "text/plain",
            )
        },
    )

    assert upload_response.status_code == 201
    source_payload = upload_response.json()
    assert source_payload["has_file"] is True
    assert source_payload["file_size"] > 0
    assert source_payload["metadata"]["storage_key"] == "uploaded-source-1/guide.txt"
    assert "file_path" not in source_payload["metadata"]

    preview_response = persisted_client.post(
        "/api/v1/sources/uploaded-source-1/index/preview",
        json={},
    )
    assert preview_response.status_code == 200
    assert preview_response.json()["effective_parser"] == "simple_directory_reader"

    index_response = persisted_client.post(
        "/api/v1/sources/uploaded-source-1/index",
        json={},
    )

    assert index_response.status_code == 200
    index_payload = index_response.json()
    assert index_payload["effective_parser"] == "simple_directory_reader"
    assert index_payload["effective_chunker"] == "fixed_token"
    assert index_payload["job"]["effective_parser"] == "simple_directory_reader"
    assert index_payload["job"]["effective_chunker"] == "fixed_token"
    assert index_payload["effective_config"]["parser"] == "simple_directory_reader"
    assert index_payload["effective_config"]["chunker"] == "fixed_token"
    assert index_payload["node_count"] > 0

    artifacts_response = persisted_client.get(
        f"/api/v1/indexing/jobs/{index_payload['job']['job_id']}/artifacts"
    )
    assert artifacts_response.status_code == 200
    artifacts = artifacts_response.json()
    assert artifacts["job"]["effective_parser"] == "simple_directory_reader"
    assert artifacts["blocks"]
    assert artifacts["nodes"]
    block_ids = {block["block_id"] for block in artifacts["blocks"]}
    node_block_ids = {
        block_id
        for node in artifacts["nodes"]
        for block_id in node["block_ids"]
    }
    assert node_block_ids <= block_ids
    assert artifacts["metrics"]["block_count"] == len(artifacts["blocks"])
    assert "parse_ms" in artifacts["metrics"]["performance"]
