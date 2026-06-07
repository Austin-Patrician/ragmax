from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.records import IndexJobRecord, IndexJobStatus, SourceRecord
from ragmax.infrastructure.db.models import IndexJobModel, IndexNodeModel, SourceModel


def _utc_now() -> datetime:
    return datetime.now(UTC)


class SqlAlchemySourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, source: SourceRecord) -> SourceRecord:
        now = _utc_now()
        model = SourceModel(
            source_id=source.source_id,
            notebook_id=source.notebook_id,
            filename=source.filename,
            media_type=source.media_type,
            source_hash=source.source_hash,
            text=source.text,
            blocks=list(source.blocks),
            file_path=source.file_path,
            file_size=source.file_size,
            source_metadata=source.metadata,
            created_at=now,
            updated_at=now,
        )
        self._session.add(model)
        return _source_record_from_model(model)

    async def get(self, source_id: str) -> SourceRecord | None:
        model = await self._session.get(SourceModel, source_id)
        if model is None:
            return None
        return _source_record_from_model(model)


class SqlAlchemyIndexJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job: IndexJobRecord) -> IndexJobRecord:
        model = IndexJobModel(
            job_id=job.job_id,
            source_id=job.source_id,
            status=job.status.value,
            requested_profile=job.requested_profile,
            effective_profile=job.effective_profile,
            requested_parser=job.requested_parser,
            effective_parser=job.effective_parser,
            overrides=job.overrides,
            summary=job.summary,
            error_message=job.error_message,
            vector_status=job.vector_status,
            vector_error_message=job.vector_error_message,
            node_count=job.node_count,
            created_at=job.created_at or _utc_now(),
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
        self._session.add(model)
        return _job_record_from_model(model)

    async def get(self, job_id: str) -> IndexJobRecord | None:
        model = await self._session.get(IndexJobModel, job_id)
        if model is None:
            return None
        return _job_record_from_model(model)

    async def update(self, job: IndexJobRecord) -> IndexJobRecord:
        model = await self._session.get(IndexJobModel, job.job_id)
        if model is None:
            raise ValueError(f"Index job does not exist: {job.job_id}")

        model.status = job.status.value
        model.requested_profile = job.requested_profile
        model.effective_profile = job.effective_profile
        model.requested_parser = job.requested_parser
        model.effective_parser = job.effective_parser
        model.overrides = job.overrides
        model.summary = job.summary
        model.error_message = job.error_message
        model.vector_status = job.vector_status
        model.vector_error_message = job.vector_error_message
        model.node_count = job.node_count
        model.started_at = job.started_at
        model.finished_at = job.finished_at
        return _job_record_from_model(model)


class SqlAlchemyIndexNodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_source(
        self,
        *,
        source_id: str,
        job_id: str,
        nodes: Sequence[IndexNode],
    ) -> tuple[IndexNode, ...]:
        await self.delete_by_source(source_id)
        models = [_node_model_from_node(node, job_id) for node in nodes]
        self._session.add_all(models)
        return tuple(nodes)

    async def list_by_source(self, source_id: str) -> tuple[IndexNode, ...]:
        result = await self._session.execute(
            select(IndexNodeModel)
            .where(IndexNodeModel.source_id == source_id)
            .order_by(IndexNodeModel.created_at, IndexNodeModel.node_id)
        )
        return tuple(_node_from_model(model) for model in result.scalars())

    async def delete_by_source(self, source_id: str) -> int:
        result = await self._session.execute(
            delete(IndexNodeModel).where(IndexNodeModel.source_id == source_id)
        )
        return int(result.rowcount or 0)


class SqlAlchemyIndexingUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlAlchemyIndexingUnitOfWork":
        self._session = self._session_factory()
        self.sources = SqlAlchemySourceRepository(self._session)
        self.jobs = SqlAlchemyIndexJobRepository(self._session)
        self.nodes = SqlAlchemyIndexNodeRepository(self._session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is None:
            return
        if exc_type is not None:
            await self.rollback()
        await self._session.close()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work session is not initialized.")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("Unit of work session is not initialized.")
        await self._session.rollback()


def _source_record_from_model(model: SourceModel) -> SourceRecord:
    return SourceRecord(
        source_id=model.source_id,
        notebook_id=model.notebook_id,
        filename=model.filename,
        media_type=model.media_type,
        source_hash=model.source_hash,
        text=model.text,
        blocks=tuple(model.blocks or ()),
        file_path=model.file_path,
        file_size=model.file_size,
        metadata=dict(model.source_metadata or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _job_record_from_model(model: IndexJobModel) -> IndexJobRecord:
    return IndexJobRecord(
        job_id=model.job_id,
        source_id=model.source_id,
        status=IndexJobStatus(model.status),
        requested_profile=model.requested_profile,
        effective_profile=model.effective_profile,
        requested_parser=model.requested_parser,
        effective_parser=model.effective_parser,
        overrides=dict(model.overrides or {}),
        summary=dict(model.summary or {}),
        error_message=model.error_message,
        vector_status=model.vector_status,
        vector_error_message=model.vector_error_message,
        node_count=model.node_count,
        created_at=model.created_at,
        started_at=model.started_at,
        finished_at=model.finished_at,
    )


def _node_model_from_node(node: IndexNode, job_id: str) -> IndexNodeModel:
    return IndexNodeModel(
        node_id=node.node_id,
        job_id=job_id,
        source_id=node.source_id,
        notebook_id=node.notebook_id,
        text=node.text,
        modality=node.modality,
        content_type=node.content_type,
        page_start=node.page_start,
        page_end=node.page_end,
        section_path=list(node.section_path),
        block_ids=list(node.block_ids),
        parent_node_id=node.parent_node_id,
        asset_path=node.asset_path,
        bbox=list(node.bbox) if node.bbox else None,
        indexing_profile=node.indexing_profile,
        parser_version=node.parser_version,
        chunker_version=node.chunker_version,
        embedding_model=node.embedding_model,
        node_metadata=node.metadata,
        created_at=_utc_now(),
    )


def _node_from_model(model: IndexNodeModel) -> IndexNode:
    bbox = tuple(model.bbox) if model.bbox else None
    return IndexNode(
        node_id=model.node_id,
        source_id=model.source_id,
        notebook_id=model.notebook_id,
        text=model.text,
        modality=model.modality,
        content_type=model.content_type,
        page_start=model.page_start,
        page_end=model.page_end,
        section_path=tuple(model.section_path or ()),
        block_ids=tuple(model.block_ids or ()),
        parent_node_id=model.parent_node_id,
        asset_path=model.asset_path,
        bbox=bbox,
        indexing_profile=model.indexing_profile,
        parser_version=model.parser_version,
        chunker_version=model.chunker_version,
        embedding_model=model.embedding_model,
        metadata=dict(model.node_metadata or {}),
    )
