import asyncio

from conftest import authenticate_test_client, db_session_override, seed_auth_user
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ragmax.api.dependencies import (
    create_indexing_service,
    get_indexing_service,
    get_source_storage,
)
from ragmax.infrastructure.db.base import Base, import_models
from ragmax.infrastructure.db.repositories.indexing import SqlAlchemyIndexingUnitOfWork
from ragmax.infrastructure.db.session import get_db_session
from ragmax.infrastructure.storage.local_indexing_artifact_storage import (
    LocalIndexingArtifactStorage,
)
from ragmax.infrastructure.storage.local_source_storage import LocalSourceStorage
from ragmax.main import create_app


def test_delete_source_removes_uploaded_file_and_indexing_artifacts(tmp_path) -> None:
    import_models()
    database_url = f"sqlite+aiosqlite:///{tmp_path}/ragmax.db"
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    source_root = tmp_path / "sources"
    artifact_root = tmp_path / "indexing-artifacts"
    source_storage = LocalSourceStorage(
        root_dir=source_root,
        max_upload_bytes=10 * 1024 * 1024,
    )
    artifact_storage = LocalIndexingArtifactStorage(root_dir=artifact_root)

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
        unit_of_work_factory=lambda: SqlAlchemyIndexingUnitOfWork(session_factory),
        artifact_storage=artifact_storage,
        source_storage=source_storage,
    )
    app.dependency_overrides[get_source_storage] = lambda: source_storage

    try:
        with TestClient(app) as client:
            authenticate_test_client(client)
            upload_response = client.post(
                "/api/v1/sources/upload",
                data={
                    "notebook_id": "notebook-1",
                    "source_id": "cleanup-source",
                },
                files={
                    "file": (
                        "cleanup.md",
                        b"# Cleanup\n\nThe source and artifacts should be deleted.",
                        "text/markdown",
                    )
                },
            )
            assert upload_response.status_code == 201, upload_response.text
            source_dir = source_root / "cleanup-source"
            assert (source_dir / "cleanup.md").exists()

            artifact_storage.write_json(
                source_id="cleanup-source",
                run_id="run_cleanup",
                stage_run_id="stage_cleanup",
                stage_name="source",
                artifact_type="source_snapshot",
                payload={"source_id": "cleanup-source"},
            )
            artifact_dir = artifact_root / "cleanup-source"
            assert artifact_dir.exists()

            delete_response = client.delete("/api/v1/sources/cleanup-source")
            assert delete_response.status_code == 204, delete_response.text
            assert not source_dir.exists()
            assert not artifact_dir.exists()
    finally:
        app.dependency_overrides.clear()
        asyncio.run(teardown_database())
