from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ragmax.domain.indexing.blocks import BlockType
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.records import (
    INDEXING_STAGE_ORDER,
    IndexArtifactManifestRecord,
    IndexBlockRecord,
    IndexingStage,
    IndexJobRecord,
    IndexJobStatus,
    IndexPipelineRunRecord,
    IndexPipelineStatus,
    IndexStageRunRecord,
    IndexStageStatus,
    SourceRecord,
)
from ragmax.infrastructure.db.models import (
    IndexArtifactManifestModel,
    IndexBlockModel,
    IndexJobModel,
    IndexNodeModel,
    IndexPipelineRunModel,
    IndexStageRunModel,
    SourceModel,
)


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
            input_blocks=list(source.input_blocks),
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

    async def list(self, limit: int = 100, offset: int = 0) -> tuple[SourceRecord, ...]:
        result = await self._session.execute(
            select(SourceModel)
            .order_by(SourceModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        models = result.scalars().all()
        return tuple(_source_record_from_model(model) for model in models)

    async def delete(self, source_id: str) -> bool:
        result = await self._session.execute(
            delete(SourceModel).where(SourceModel.source_id == source_id)
        )
        return result.rowcount > 0


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


class SqlAlchemyIndexPipelineRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: IndexPipelineRunRecord) -> IndexPipelineRunRecord:
        model = IndexPipelineRunModel(
            run_id=run.run_id,
            source_id=run.source_id,
            status=run.status.value,
            requested_profile=run.requested_profile,
            effective_profile=run.effective_profile,
            requested_parser=run.requested_parser,
            effective_parser=run.effective_parser,
            overrides=run.overrides,
            summary=run.summary,
            error_message=run.error_message,
            created_at=run.created_at or _utc_now(),
            started_at=run.started_at,
            finished_at=run.finished_at,
        )
        self._session.add(model)
        return _pipeline_run_record_from_model(model)

    async def get(self, run_id: str) -> IndexPipelineRunRecord | None:
        model = await self._session.get(IndexPipelineRunModel, run_id)
        if model is None:
            return None
        return _pipeline_run_record_from_model(model)

    async def list_by_source(
        self,
        source_id: str,
        *,
        limit: int,
    ) -> tuple[IndexPipelineRunRecord, ...]:
        result = await self._session.execute(
            select(IndexPipelineRunModel)
            .where(IndexPipelineRunModel.source_id == source_id)
            .order_by(IndexPipelineRunModel.created_at.desc())
            .limit(limit)
        )
        return tuple(_pipeline_run_record_from_model(model) for model in result.scalars())

    async def update(self, run: IndexPipelineRunRecord) -> IndexPipelineRunRecord:
        model = await self._session.get(IndexPipelineRunModel, run.run_id)
        if model is None:
            raise ValueError(f"Index pipeline run does not exist: {run.run_id}")

        model.status = run.status.value
        model.requested_profile = run.requested_profile
        model.effective_profile = run.effective_profile
        model.requested_parser = run.requested_parser
        model.effective_parser = run.effective_parser
        model.overrides = run.overrides
        model.summary = run.summary
        model.error_message = run.error_message
        model.started_at = run.started_at
        model.finished_at = run.finished_at
        return _pipeline_run_record_from_model(model)


class SqlAlchemyIndexStageRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, stage_run: IndexStageRunRecord) -> IndexStageRunRecord:
        model = IndexStageRunModel(
            stage_run_id=stage_run.stage_run_id,
            run_id=stage_run.run_id,
            stage_name=stage_run.stage_name.value,
            status=stage_run.status.value,
            sequence_no=stage_run.sequence_no,
            stale=stage_run.stale,
            summary=stage_run.summary,
            error_message=stage_run.error_message,
            started_at=stage_run.started_at,
            finished_at=stage_run.finished_at,
            duration_ms=stage_run.duration_ms,
            artifact_count=stage_run.artifact_count,
            created_at=stage_run.created_at or _utc_now(),
        )
        self._session.add(model)
        return _stage_run_record_from_model(model)

    async def get(self, stage_run_id: str) -> IndexStageRunRecord | None:
        model = await self._session.get(IndexStageRunModel, stage_run_id)
        if model is None:
            return None
        return _stage_run_record_from_model(model)

    async def list_by_run(self, run_id: str) -> tuple[IndexStageRunRecord, ...]:
        result = await self._session.execute(
            select(IndexStageRunModel)
            .where(IndexStageRunModel.run_id == run_id)
            .order_by(IndexStageRunModel.stage_name, IndexStageRunModel.sequence_no)
        )
        return tuple(
            sorted(
                (_stage_run_record_from_model(model) for model in result.scalars()),
                key=lambda stage_run: (
                    _stage_order_index(stage_run.stage_name),
                    stage_run.sequence_no,
                ),
            )
        )

    async def latest_for_stage(
        self,
        *,
        run_id: str,
        stage_name: IndexingStage,
    ) -> IndexStageRunRecord | None:
        result = await self._session.execute(
            select(IndexStageRunModel)
            .where(
                IndexStageRunModel.run_id == run_id,
                IndexStageRunModel.stage_name == stage_name.value,
            )
            .order_by(IndexStageRunModel.sequence_no.desc())
            .limit(1)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return _stage_run_record_from_model(model)

    async def update(self, stage_run: IndexStageRunRecord) -> IndexStageRunRecord:
        model = await self._session.get(IndexStageRunModel, stage_run.stage_run_id)
        if model is None:
            raise ValueError(f"Index stage run does not exist: {stage_run.stage_run_id}")

        model.status = stage_run.status.value
        model.stale = stage_run.stale
        model.summary = stage_run.summary
        model.error_message = stage_run.error_message
        model.started_at = stage_run.started_at
        model.finished_at = stage_run.finished_at
        model.duration_ms = stage_run.duration_ms
        model.artifact_count = stage_run.artifact_count
        return _stage_run_record_from_model(model)

    async def mark_stale_after(
        self,
        *,
        run_id: str,
        stage_name: IndexingStage,
    ) -> int:
        stale_stage_names = [
            stage.value
            for stage in INDEXING_STAGE_ORDER
            if _stage_order_index(stage) > _stage_order_index(stage_name)
        ]
        if not stale_stage_names:
            return 0

        result = await self._session.execute(
            update(IndexStageRunModel)
            .where(
                IndexStageRunModel.run_id == run_id,
                IndexStageRunModel.stage_name.in_(stale_stage_names),
            )
            .values(stale=True)
        )
        return int(result.rowcount or 0)


class SqlAlchemyIndexArtifactManifestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(
        self,
        manifests: Sequence[IndexArtifactManifestRecord],
    ) -> tuple[IndexArtifactManifestRecord, ...]:
        models = [_artifact_manifest_model_from_record(manifest) for manifest in manifests]
        self._session.add_all(models)
        return tuple(manifests)

    async def get(self, artifact_id: str) -> IndexArtifactManifestRecord | None:
        model = await self._session.get(IndexArtifactManifestModel, artifact_id)
        if model is None:
            return None
        return _artifact_manifest_record_from_model(model)

    async def list_by_stage_run(
        self,
        stage_run_id: str,
    ) -> tuple[IndexArtifactManifestRecord, ...]:
        result = await self._session.execute(
            select(IndexArtifactManifestModel)
            .where(IndexArtifactManifestModel.stage_run_id == stage_run_id)
            .order_by(IndexArtifactManifestModel.created_at, IndexArtifactManifestModel.artifact_id)
        )
        return tuple(_artifact_manifest_record_from_model(model) for model in result.scalars())

    async def list_latest_by_run_stage(
        self,
        *,
        run_id: str,
        stage_name: IndexingStage,
    ) -> tuple[IndexArtifactManifestRecord, ...]:
        stage_result = await self._session.execute(
            select(IndexStageRunModel.stage_run_id)
            .where(
                IndexStageRunModel.run_id == run_id,
                IndexStageRunModel.stage_name == stage_name.value,
            )
            .order_by(IndexStageRunModel.sequence_no.desc())
            .limit(1)
        )
        stage_run_id = stage_result.scalar_one_or_none()
        if stage_run_id is None:
            return ()
        return await self.list_by_stage_run(stage_run_id)


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

    async def list_by_job(self, job_id: str) -> tuple[IndexNode, ...]:
        result = await self._session.execute(
            select(IndexNodeModel)
            .where(IndexNodeModel.job_id == job_id)
            .order_by(IndexNodeModel.created_at, IndexNodeModel.node_id)
        )
        return tuple(_node_from_model(model) for model in result.scalars())

    async def get_many(self, node_ids: Sequence[str]) -> tuple[IndexNode, ...]:
        if not node_ids:
            return ()
        result = await self._session.execute(
            select(IndexNodeModel).where(IndexNodeModel.node_id.in_(node_ids))
        )
        return tuple(_node_from_model(model) for model in result.scalars())

    async def delete_by_source(self, source_id: str) -> int:
        result = await self._session.execute(
            delete(IndexNodeModel).where(IndexNodeModel.source_id == source_id)
        )
        return int(result.rowcount or 0)


class SqlAlchemyIndexBlockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_for_source(
        self,
        *,
        source_id: str,
        job_id: str,
        blocks: Sequence[IndexBlockRecord],
    ) -> tuple[IndexBlockRecord, ...]:
        await self.delete_by_source(source_id)
        models = [_block_model_from_record(block, job_id) for block in blocks]
        self._session.add_all(models)
        return tuple(blocks)

    async def list_by_job(self, job_id: str) -> tuple[IndexBlockRecord, ...]:
        result = await self._session.execute(
            select(IndexBlockModel)
            .where(IndexBlockModel.job_id == job_id)
            .order_by(IndexBlockModel.order_index, IndexBlockModel.block_id)
        )
        return tuple(_block_record_from_model(model) for model in result.scalars())

    async def delete_by_source(self, source_id: str) -> int:
        result = await self._session.execute(
            delete(IndexBlockModel).where(IndexBlockModel.source_id == source_id)
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
        self.pipeline_runs = SqlAlchemyIndexPipelineRunRepository(self._session)
        self.stage_runs = SqlAlchemyIndexStageRunRepository(self._session)
        self.artifact_manifests = SqlAlchemyIndexArtifactManifestRepository(self._session)
        self.blocks = SqlAlchemyIndexBlockRepository(self._session)
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
        input_blocks=tuple(model.input_blocks or ()),
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


def _pipeline_run_record_from_model(model: IndexPipelineRunModel) -> IndexPipelineRunRecord:
    return IndexPipelineRunRecord(
        run_id=model.run_id,
        source_id=model.source_id,
        status=IndexPipelineStatus(model.status),
        requested_profile=model.requested_profile,
        effective_profile=model.effective_profile,
        requested_parser=model.requested_parser,
        effective_parser=model.effective_parser,
        overrides=dict(model.overrides or {}),
        summary=dict(model.summary or {}),
        error_message=model.error_message,
        created_at=model.created_at,
        started_at=model.started_at,
        finished_at=model.finished_at,
    )


def _stage_run_record_from_model(model: IndexStageRunModel) -> IndexStageRunRecord:
    return IndexStageRunRecord(
        stage_run_id=model.stage_run_id,
        run_id=model.run_id,
        stage_name=IndexingStage(model.stage_name),
        status=IndexStageStatus(model.status),
        sequence_no=model.sequence_no,
        stale=model.stale,
        summary=dict(model.summary or {}),
        error_message=model.error_message,
        started_at=model.started_at,
        finished_at=model.finished_at,
        duration_ms=model.duration_ms,
        artifact_count=model.artifact_count,
        created_at=model.created_at,
    )


def _artifact_manifest_model_from_record(
    manifest: IndexArtifactManifestRecord,
) -> IndexArtifactManifestModel:
    return IndexArtifactManifestModel(
        artifact_id=manifest.artifact_id,
        run_id=manifest.run_id,
        stage_run_id=manifest.stage_run_id,
        stage_name=manifest.stage_name.value,
        artifact_type=manifest.artifact_type,
        storage_uri=manifest.storage_uri,
        payload_format=manifest.payload_format,
        content_hash=manifest.content_hash,
        size_bytes=manifest.size_bytes,
        record_count=manifest.record_count,
        preview=manifest.preview,
        created_at=manifest.created_at or _utc_now(),
    )


def _artifact_manifest_record_from_model(
    model: IndexArtifactManifestModel,
) -> IndexArtifactManifestRecord:
    return IndexArtifactManifestRecord(
        artifact_id=model.artifact_id,
        run_id=model.run_id,
        stage_run_id=model.stage_run_id,
        stage_name=IndexingStage(model.stage_name),
        artifact_type=model.artifact_type,
        storage_uri=model.storage_uri,
        payload_format=model.payload_format,
        content_hash=model.content_hash,
        size_bytes=model.size_bytes,
        record_count=model.record_count,
        preview=dict(model.preview or {}),
        created_at=model.created_at,
    )


def _stage_order_index(stage_name: IndexingStage) -> int:
    return INDEXING_STAGE_ORDER.index(stage_name)


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


def _block_model_from_record(block: IndexBlockRecord, job_id: str) -> IndexBlockModel:
    return IndexBlockModel(
        block_id=block.block_id,
        job_id=job_id,
        source_id=block.source_id,
        notebook_id=block.notebook_id,
        order_index=block.order_index,
        block_type=block.block_type.value,
        text=block.text,
        page_no=block.page_no,
        bbox=list(block.bbox) if block.bbox else None,
        section_hint=list(block.section_hint),
        parser_name=block.parser_name,
        parser_version=block.parser_version,
        content_hash=block.content_hash,
        block_metadata=block.metadata,
        created_at=_utc_now(),
    )


def _block_record_from_model(model: IndexBlockModel) -> IndexBlockRecord:
    bbox = tuple(model.bbox) if model.bbox else None
    return IndexBlockRecord(
        block_id=model.block_id,
        job_id=model.job_id,
        source_id=model.source_id,
        notebook_id=model.notebook_id,
        order_index=model.order_index,
        block_type=BlockType(model.block_type),
        text=model.text,
        page_no=model.page_no,
        bbox=bbox,
        section_hint=tuple(model.section_hint or ()),
        parser_name=model.parser_name,
        parser_version=model.parser_version,
        content_hash=model.content_hash,
        metadata=dict(model.block_metadata or {}),
        created_at=model.created_at,
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
