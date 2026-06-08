import asyncio
from collections.abc import Iterator

import pytest
from conftest import (
    TEST_PASSWORD,
    TEST_USERNAME,
    authenticate_test_client,
    db_session_override,
    seed_auth_user,
)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ragmax.infrastructure.db.base import Base, import_models
from ragmax.infrastructure.db.session import get_db_session
from ragmax.main import create_app


def test_login_returns_access_token_and_refresh_cookie(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 900
    assert payload["user"]["username"] == TEST_USERNAME
    assert payload["user"]["route_permissions"] == [
        "/indexing",
        "/retrieval",
        "/evaluation",
    ]
    assert "httponly" in response.headers["set-cookie"].lower()


def test_protected_route_requires_access_token(client: TestClient) -> None:
    client.headers.pop("Authorization", None)

    response = client.get("/api/v1/indexing/profiles")

    assert response.status_code == 401


def test_route_permission_is_enforced_before_business_handler(
    indexing_only_client: TestClient,
) -> None:
    allowed_response = indexing_only_client.get("/api/v1/indexing/profiles")
    denied_response = indexing_only_client.post(
        "/api/v1/retrieval/search",
        json={"query": "cash flow", "notebook_id": "notebook-1"},
    )
    evaluation_denied_response = indexing_only_client.get("/api/v1/evaluation/datasets")

    assert allowed_response.status_code == 200
    assert denied_response.status_code == 403
    assert evaluation_denied_response.status_code == 403


def test_refresh_rotates_refresh_token(client: TestClient) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    old_refresh_token = login_response.cookies.get("ragmax_refresh_token")
    assert old_refresh_token

    refresh_response = client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 200
    new_refresh_token = refresh_response.cookies.get("ragmax_refresh_token")
    assert new_refresh_token
    assert new_refresh_token != old_refresh_token

    client.cookies.set("ragmax_refresh_token", old_refresh_token, path="/api/v1/auth")
    old_refresh_response = client.post("/api/v1/auth/refresh")
    assert old_refresh_response.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    logout_response = client.post("/api/v1/auth/logout")
    client.headers.pop("Authorization", None)
    refresh_response = client.post("/api/v1/auth/refresh")

    assert logout_response.status_code == 204
    assert refresh_response.status_code == 401


@pytest.fixture
def indexing_only_client(tmp_path) -> Iterator[TestClient]:
    import_models()
    database_url = f"sqlite+aiosqlite:///{tmp_path}/ragmax.db"
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def setup_database() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def teardown_database() -> None:
        await engine.dispose()

    asyncio.run(setup_database())
    seed_auth_user(session_factory, routes=["/indexing"])

    app = create_app()
    app.dependency_overrides[get_db_session] = db_session_override(session_factory)

    with TestClient(app) as test_client:
        authenticate_test_client(test_client)
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(teardown_database())
