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
from ragmax.infrastructure.db.repositories.indexing import SqlAlchemyIndexingUnitOfWork
from ragmax.infrastructure.storage.local_source_storage import LocalSourceStorage
from ragmax.main import create_app


@pytest.fixture(autouse=True)
def isolate_runtime_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("VECTOR_INDEX_ENABLED", "false")
    monkeypatch.setenv("RETRIEVAL_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


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

    app = create_app()
    app.dependency_overrides[get_indexing_service] = lambda: create_indexing_service(
        unit_of_work_factory=lambda: SqlAlchemyIndexingUnitOfWork(session_factory)
    )
    app.dependency_overrides[get_source_storage] = lambda: LocalSourceStorage(
        root_dir=tmp_path / "storage",
        max_upload_bytes=10 * 1024 * 1024,
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(teardown_database())
