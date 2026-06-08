from fastapi.testclient import TestClient


def test_indexing_profiles(client: TestClient) -> None:
    response = client.get("/api/v1/indexing/profiles")

    assert response.status_code == 200
    profiles = response.json()
    assert all("parser" not in profile for profile in profiles)
    assert all("node_graph_mode" in profile for profile in profiles)
    assert any(
        profile["name"] == "section_pdf"
        and profile["node_graph_mode"] == "parent_child"
        for profile in profiles
    )
    assert {profile["name"] for profile in profiles} == {
        "default_pdf",
        "section_pdf",
        "table_report",
        "scanned_pdf",
    }
