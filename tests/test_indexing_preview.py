from fastapi.testclient import TestClient


def test_indexing_preview_auto_selects_section_profile(client: TestClient) -> None:
    response = client.post(
        "/api/v1/indexing/preview",
        json={
            "source": {
                "source_id": "source-1",
                "notebook_id": "notebook-1",
                "filename": "guide.md",
                "media_type": "text/markdown",
                "text": (
                    "# Introduction\n\n"
                    "RAG systems combine retrieval and generation for grounded answers.\n\n"
                    "## Methods\n\n"
                    "Chunking quality strongly affects recall and citation quality.\n\n"
                    "## Evaluation\n\n"
                    "Use representative questions and inspect the retrieved chunks."
                ),
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["recommended_profile"] == "section_pdf"
    assert payload["effective_profile"]["name"] == "section_pdf"
    assert payload["summary"]["node_count"] >= 2
    assert any(node["content_type"] == "section" for node in payload["nodes"])


def test_indexing_preview_detects_table_profile(client: TestClient) -> None:
    response = client.post(
        "/api/v1/indexing/preview",
        json={
            "source": {
                "source_id": "source-2",
                "notebook_id": "notebook-1",
                "filename": "report.md",
                "media_type": "text/markdown",
                "blocks": [
                    {
                        "block_type": "heading",
                        "text": "# Metrics",
                        "page_no": 1,
                    },
                    {
                        "block_type": "table",
                        "text": (
                            "| Metric | Value |\n"
                            "| --- | --- |\n"
                            "| Recall | 0.92 |\n"
                            "| Precision | 0.88 |\n"
                            "| Coverage | 0.95 |"
                        ),
                        "page_no": 1,
                    },
                ],
            }
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis"]["recommended_profile"] == "table_report"
    assert payload["effective_profile"]["name"] == "table_report"
    assert any(node["content_type"] == "table" for node in payload["nodes"])


def test_indexing_preview_rejects_empty_source(client: TestClient) -> None:
    response = client.post(
        "/api/v1/indexing/preview",
        json={
            "source": {
                "source_id": "source-3",
                "notebook_id": "notebook-1",
                "filename": "empty.txt",
                "media_type": "text/plain",
            }
        },
    )

    assert response.status_code == 422
