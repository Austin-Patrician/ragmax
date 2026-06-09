from fastapi.testclient import TestClient


def test_user_settings_profile_returns_current_user(client: TestClient) -> None:
    response = client.get("/api/v1/user-settings/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "test-user"
    assert "/indexing" in payload["route_permissions"]


def test_runtime_configuration_can_override_and_clear(client: TestClient) -> None:
    initial_response = client.get("/api/v1/user-settings/configuration")
    assert initial_response.status_code == 200
    initial_fields = {field["key"]: field for field in initial_response.json()["fields"]}
    assert initial_fields["qdrant_url"]["source"] == "env"

    update_response = client.patch(
        "/api/v1/user-settings/configuration",
        json={"values": {"qdrant_url": "http://qdrant.local:6333"}},
    )
    assert update_response.status_code == 200
    updated_fields = {field["key"]: field for field in update_response.json()["fields"]}
    assert updated_fields["qdrant_url"]["source"] == "db"
    assert updated_fields["qdrant_url"]["value"] == "http://qdrant.local:6333"

    clear_response = client.patch(
        "/api/v1/user-settings/configuration",
        json={"values": {"qdrant_url": None}},
    )
    assert clear_response.status_code == 200
    cleared_fields = {field["key"]: field for field in clear_response.json()["fields"]}
    assert cleared_fields["qdrant_url"]["source"] == "env"


def test_model_provider_model_and_default_binding_crud(client: TestClient) -> None:
    provider_response = client.post(
        "/api/v1/user-settings/model-providers",
        json={
            "name": "OpenAI Test",
            "provider_type": "openai_compatible",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-secret",
        },
    )
    assert provider_response.status_code == 201
    provider = provider_response.json()["providers"][0]
    assert provider["api_key_configured"] is True
    assert provider["api_key_masked"] == "sk-t...cret"

    model_response = client.post(
        f"/api/v1/user-settings/model-providers/{provider['provider_id']}/models",
        json={
            "model_name": "gpt-4o-mini",
            "display_name": "GPT 4o mini",
            "ai_type": "llm",
        },
    )
    assert model_response.status_code == 201
    model = model_response.json()["providers"][0]["models"][0]

    defaults_response = client.patch(
        "/api/v1/user-settings/model-providers/defaults",
        json={"bindings": {"answer_llm": model["model_id"]}},
    )
    assert defaults_response.status_code == 200
    defaults = defaults_response.json()["defaults"]
    assert defaults == [
        {
            "binding_key": "answer_llm",
            "model_id": model["model_id"],
            "updated_by": "user_test",
            "created_at": defaults[0]["created_at"],
            "updated_at": defaults[0]["updated_at"],
        }
    ]
