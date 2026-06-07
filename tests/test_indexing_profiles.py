from fastapi.testclient import TestClient


def test_indexing_profiles(client: TestClient) -> None:
    response = client.get("/api/v1/indexing/profiles")

    assert response.status_code == 200
    profiles = response.json()
    assert all("parser" in profile for profile in profiles)
    assert {profile["name"] for profile in profiles} == {
        "default_pdf",
        "section_pdf",
        "table_report",
        "scanned_pdf",
    }
