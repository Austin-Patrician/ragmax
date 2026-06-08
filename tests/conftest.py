import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ragmax.api.dependencies import (
    create_indexing_service,
    get_indexing_service,
    get_source_storage,
)
from ragmax.core.config import get_settings
from ragmax.infrastructure.db.base import Base, import_models
from ragmax.infrastructure.db.repositories.auth import bootstrap_auth_user
from ragmax.infrastructure.db.repositories.indexing import SqlAlchemyIndexingUnitOfWork
from ragmax.infrastructure.db.session import get_db_session
from ragmax.infrastructure.storage.local_source_storage import LocalSourceStorage
from ragmax.main import create_app

TEST_USERNAME = "test-user"
TEST_PASSWORD = "test-password"
TEST_ROUTE_PERMISSIONS = ["/indexing", "/retrieval", "/evaluation"]


@pytest.fixture(autouse=True)
def isolate_runtime_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("VECTOR_INDEX_ENABLED", "false")
    monkeypatch.setenv("RETRIEVAL_ENABLED", "false")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("AUTH_BOOTSTRAP_USERNAME", "")
    monkeypatch.setenv("AUTH_BOOTSTRAP_PASSWORD", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
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
    seed_auth_user(session_factory)

    app = create_app()
    app.dependency_overrides[get_db_session] = db_session_override(session_factory)

    with TestClient(app) as test_client:
        authenticate_test_client(test_client)
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(teardown_database())


@pytest.fixture
def persisted_client(tmp_path) -> Iterator[TestClient]:
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
    seed_auth_user(session_factory)

    app = create_app()
    app.dependency_overrides[get_db_session] = db_session_override(session_factory)
    app.dependency_overrides[get_indexing_service] = lambda: create_indexing_service(
        unit_of_work_factory=lambda: SqlAlchemyIndexingUnitOfWork(session_factory)
    )
    app.dependency_overrides[get_source_storage] = lambda: LocalSourceStorage(
        root_dir=tmp_path / "storage",
        max_upload_bytes=10 * 1024 * 1024,
    )

    with TestClient(app) as test_client:
        authenticate_test_client(test_client)
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(teardown_database())


def db_session_override(session_factory: async_sessionmaker):
    async def override():
        async with session_factory() as session:
            yield session

    return override


def seed_auth_user(
    session_factory: async_sessionmaker,
    *,
    routes: list[str] | None = None,
) -> None:
    asyncio.run(
        bootstrap_auth_user(
            session_factory,
            username=TEST_USERNAME,
            password=TEST_PASSWORD,
            routes=routes or TEST_ROUTE_PERMISSIONS,
        )
    )


def authenticate_test_client(test_client: TestClient) -> None:
    response = test_client.post(
        "/api/v1/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    test_client.headers.update(
        {"Authorization": f"Bearer {response.json()['access_token']}"}
    )
