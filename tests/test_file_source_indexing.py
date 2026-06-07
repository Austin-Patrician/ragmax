from fastapi.testclient import TestClient


def test_indexing_parsers_lists_user_visible_parsers(client: TestClient) -> None:
    response = client.get("/api/v1/indexing/parsers")

    assert response.status_code == 200
    parsers = response.json()
    parser_names = {parser["name"] for parser in parsers}
    assert parser_names == {"simple_directory_reader", "llamaparse"}
    assert "inline_content_parser" not in parser_names
    assert any(
        parser["name"] == "simple_directory_reader" and parser["is_default"]
        for parser in parsers
    )


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
    assert index_payload["job"]["effective_parser"] == "simple_directory_reader"
    assert index_payload["effective_profile"]["parser"] == "simple_directory_reader"
    assert index_payload["node_count"] > 0
