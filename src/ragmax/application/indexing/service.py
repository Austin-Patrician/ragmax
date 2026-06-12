import hashlib
import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import asdict, replace
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from ragmax.application.indexing.dtos import (
    CreateIndexPipelineRunCommand,
    CreateSourceCommand,
    DeleteSourceIndexResult,
    IndexArtifactDataResult,
    IndexingArtifactsResult,
    IndexPipelineRunResult,
    PreviewIndexingCommand,
    PreviewIndexingResult,
    RunIndexJobCommand,
    RunIndexJobResult,
    SourceInput,
    SourceInputBlock,
    StageArtifactsResult,
)
from ragmax.application.indexing.parser_registry import SourceParserRegistry
from ragmax.application.indexing.ports import (
    EmbeddingProvider,
    IndexingUnitOfWork,
    VectorIndexWriter,
)
from ragmax.core.exceptions import ConfigurationError, InvalidRequestError, NotFoundError
from ragmax.domain.indexing.blocks import ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.ports import Chunker, NodeEnricher
from ragmax.domain.indexing.quality import QualityThresholds, calculate_chunk_quality
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
from ragmax.domain.indexing.summary import IndexingSummary

IndexingUnitOfWorkFactory = Callable[[], IndexingUnitOfWork]
logger = logging.getLogger(__name__)


class IndexingService:
    def __init__(
        self,
        *,
        source_parser_registry: SourceParserRegistry,
        chunkers: Mapping[str, Chunker],
        node_enricher: NodeEnricher,
        embedding_provider: EmbeddingProvider | None = None,
        vector_index_writer: VectorIndexWriter | None = None,
        unit_of_work_factory: IndexingUnitOfWorkFactory | None = None,
        artifact_storage: Any | None = None,
        source_storage: Any | None = None,
        modal_processor: Any | None = None,
    ) -> None:
        self._source_parser_registry = source_parser_registry
        self._chunkers = dict(chunkers)
        self._node_enricher = node_enricher
        self._embedding_provider = embedding_provider
        self._vector_index_writer = vector_index_writer
        self._unit_of_work_factory = unit_of_work_factory
        self._artifact_storage = artifact_storage
        self._source_storage = source_storage
        self._modal_processor = modal_processor

    def list_parsers(self):
        return self._source_parser_registry.list()

    def _create_tokenizer(self, model_name: str):
        """创建Tokenizer实例用于精确的Token级别文本处理

        Args:
            model_name: Tokenizer模型名称，如 "cl100k_base"

        Returns:
            Tokenizer实例
        """
        from ragmax.domain.indexing.tokenization import TiktokenTokenizer
        return TiktokenTokenizer(model_name)

    async def preview(self, command: PreviewIndexingCommand) -> PreviewIndexingResult:
        return await self._build_preview(command)

    async def create_source(self, command: CreateSourceCommand) -> SourceRecord:
        self._ensure_persistence_configured()

        source_id = command.source_id or f"src_{uuid4().hex}"
        source_record = SourceRecord(
            source_id=source_id,
            notebook_id=command.notebook_id,
            filename=command.filename,
            media_type=command.media_type,
            source_hash=self._build_source_hash(
                command.text,
                command.input_blocks,
                provided_hash=command.source_hash,
            ),
            text=command.text,
            input_blocks=tuple(asdict(block) for block in command.input_blocks),
            file_path=command.file_path,
            file_size=command.file_size,
            metadata=command.metadata,
        )

        async with self._unit_of_work_factory() as uow:
            created_source = await uow.sources.create(source_record)
            await uow.commit()
            return created_source

    async def create_pipeline_run(
        self,
        command: CreateIndexPipelineRunCommand,
    ) -> IndexPipelineRunResult:
        self._ensure_persistence_configured()
        source = await self._get_source_or_raise(command.source_id)

        # 导入默认配置
        from ragmax.core.defaults import (
            DEFAULT_CHUNKER,
            get_default_chunk_config,
            get_default_parser,
        )

        # 解析配置
        parser = command.parser or get_default_parser(source.media_type)
        parser_config = command.parser_config or {}
        chunker = command.chunker or DEFAULT_CHUNKER
        chunk_config = command.chunk_config or get_default_chunk_config(chunker)

        # 创建run record
        run = IndexPipelineRunRecord(
            run_id=f"run_{uuid4().hex}",
            source_id=source.source_id,
            status=IndexPipelineStatus.PENDING,
            config={
                "parser": parser,
                "parser_config": parser_config,
                "chunker": chunker,
                "chunk_config": chunk_config,
            },
            created_at=datetime.now(UTC),
        )

        async with self._unit_of_work_factory() as uow:
            created_run = await uow.pipeline_runs.create(run)
            stages: list[IndexStageRunRecord] = []
            for stage in INDEXING_STAGE_ORDER:
                stages.append(
                    await uow.stage_runs.create(
                        IndexStageRunRecord(
                            stage_run_id=f"stage_{uuid4().hex}",
                            run_id=created_run.run_id,
                            stage_name=stage,
                            status=IndexStageStatus.PENDING,
                            sequence_no=1,
                            created_at=datetime.now(UTC),
                        )
                    )
                )
            await uow.commit()
            return IndexPipelineRunResult(run=created_run, stages=tuple(stages))

    async def list_pipeline_runs(
        self,
        source_id: str,
        *,
        limit: int,
    ) -> tuple[IndexPipelineRunRecord, ...]:
        self._ensure_persistence_configured()
        await self._get_source_or_raise(source_id)
        async with self._unit_of_work_factory() as uow:
            return await uow.pipeline_runs.list_by_source(source_id, limit=limit)

    async def list_latest_pipeline_runs(
        self,
        *,
        limit: int = 100,
    ) -> tuple[IndexPipelineRunRecord, ...]:
        self._ensure_persistence_configured()
        async with self._unit_of_work_factory() as uow:
            return await uow.pipeline_runs.list_latest(limit=limit)

    async def get_pipeline_run(self, run_id: str) -> IndexPipelineRunResult:
        self._ensure_persistence_configured()
        async with self._unit_of_work_factory() as uow:
            run = await uow.pipeline_runs.get(run_id)
            if run is None:
                raise NotFoundError(f"Index pipeline run not found: {run_id}")
            stages = await uow.stage_runs.list_by_run(run_id)
            return IndexPipelineRunResult(run=run, stages=stages)

    async def get_stage_artifacts(
        self,
        run_id: str,
        stage_name: str,
    ) -> StageArtifactsResult:
        self._ensure_persistence_configured()
        stage = _parse_stage(stage_name)
        async with self._unit_of_work_factory() as uow:
            run = await uow.pipeline_runs.get(run_id)
            if run is None:
                raise NotFoundError(f"Index pipeline run not found: {run_id}")
            stage_run = await uow.stage_runs.latest_for_stage(
                run_id=run_id,
                stage_name=stage,
            )
            if stage_run is None:
                return StageArtifactsResult(stage_run=None, manifests=())
            manifests = await uow.artifact_manifests.list_by_stage_run(stage_run.stage_run_id)
            return StageArtifactsResult(stage_run=stage_run, manifests=manifests)

    async def execute_pipeline_run(self, run_id: str) -> IndexPipelineRunResult:
        self._ensure_persistence_configured()
        self._ensure_artifact_storage_configured()
        run = await self._get_pipeline_run_or_raise(run_id)
        source = await self._get_source_or_raise(run.source_id)
        run = await self._execute_all_pipeline_stages(run=run, source=source)
        async with self._unit_of_work_factory() as uow:
            stages = await uow.stage_runs.list_by_run(run.run_id)
        return IndexPipelineRunResult(run=run, stages=stages)

    async def execute_pipeline_stage(
        self,
        run_id: str,
        stage_name: str,
    ) -> StageArtifactsResult:
        self._ensure_persistence_configured()
        self._ensure_artifact_storage_configured()
        run = await self._get_pipeline_run_or_raise(run_id)
        source = await self._get_source_or_raise(run.source_id)
        stage = _parse_stage(stage_name)
        _, stage_run, manifests = await self._execute_pipeline_stage_once(
            run=run,
            source=source,
            stage=stage,
        )
        return StageArtifactsResult(stage_run=stage_run, manifests=tuple(manifests))

    async def get_artifact_data(
        self,
        artifact_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> IndexArtifactDataResult:
        self._ensure_persistence_configured()
        self._ensure_artifact_storage_configured()
        async with self._unit_of_work_factory() as uow:
            manifest = await uow.artifact_manifests.get(artifact_id)
            if manifest is None:
                raise NotFoundError(f"Indexing artifact not found: {artifact_id}")

        if manifest.payload_format == "json":
            return IndexArtifactDataResult(
                manifest=manifest,
                data=self._artifact_storage.read_json(manifest.storage_uri),
                has_more=False,
            )

        records, has_more = self._artifact_storage.read_jsonl(
            manifest.storage_uri,
            offset=offset,
            limit=limit,
        )
        return IndexArtifactDataResult(manifest=manifest, data=records, has_more=has_more)

    async def run_index_job(self, command: RunIndexJobCommand) -> RunIndexJobResult:
        self._ensure_persistence_configured()

        source = await self._get_source_or_raise(command.source_id)
        job = IndexJobRecord(
            job_id=f"job_{uuid4().hex}",
            source_id=source.source_id,
            status=IndexJobStatus.RUNNING,
            requested_chunker=command.chunker,
            requested_parser=command.parser,
            config={
                "parser": command.parser,
                "parser_config": command.parser_config,
                "chunker": command.chunker,
                "chunk_config": command.chunk_config,
            },
            started_at=datetime.now(UTC),
        )

        async with self._unit_of_work_factory() as uow:
            job = await uow.jobs.create(job)
            await uow.commit()

        vector_status: str | None = None
        vector_error_message: str | None = None
        try:
            preview_result = await self._build_preview(
                PreviewIndexingCommand(
                    source=self._source_input_from_record(source),
                    parser=command.parser,
                    parser_config=command.parser_config,
                    chunker=command.chunker,
                    chunk_config=command.chunk_config,
                )
            )
            vector_status = "running"
            vector_started_at = perf_counter()
            indexed_nodes, vector_status, vector_count = await self._index_vectors_if_enabled(
                nodes=preview_result.nodes,
                collection_name="ragmax_text_nodes",
            )
            vector_ms = _elapsed_ms(vector_started_at)
        except Exception as exc:
            if vector_status == "running":
                vector_status = "failed"
                vector_error_message = str(exc)
            failed_job = replace(
                job,
                status=IndexJobStatus.FAILED,
                error_message=str(exc),
                vector_status=vector_status,
                vector_error_message=vector_error_message,
                finished_at=datetime.now(UTC),
            )
            async with self._unit_of_work_factory() as uow:
                await uow.jobs.update(failed_job)
                await uow.commit()
            raise

        succeeded_summary = replace(
            preview_result.summary,
            vectorized_count=vector_count,
            performance={
                **preview_result.summary.performance,
                "vector_ms": vector_ms,
            },
        )
        summary_dict = asdict(succeeded_summary)
        summary_dict["vector_index"] = {
            "status": vector_status,
            "embedding_model": self._embedding_provider.model_name
            if self._embedding_provider is not None
            else None,
            "node_count": vector_count,
            "collection": "ragmax_text_nodes" if vector_status == "succeeded" else None,
        }
        succeeded_job = replace(
            job,
            status=IndexJobStatus.SUCCEEDED,
            effective_chunker=preview_result.effective_chunker,
            effective_parser=preview_result.effective_parser,
            config=preview_result.effective_config,
            summary=summary_dict,
            vector_status=vector_status,
            node_count=len(indexed_nodes),
            finished_at=datetime.now(UTC),
        )

        async with self._unit_of_work_factory() as uow:
            await uow.blocks.replace_for_source(
                source_id=source.source_id,
                job_id=succeeded_job.job_id,
                blocks=_index_block_records_from_document(
                    job_id=succeeded_job.job_id,
                    document=preview_result.document,
                ),
            )
            await uow.nodes.replace_for_source(
                source_id=source.source_id,
                job_id=succeeded_job.job_id,
                nodes=indexed_nodes,
            )
            succeeded_job = await uow.jobs.update(succeeded_job)
            await uow.commit()

        return RunIndexJobResult(
            job=succeeded_job,
            source=source,
            effective_parser=preview_result.effective_parser,
            effective_chunker=preview_result.effective_chunker,
            effective_config=preview_result.effective_config,
            nodes=indexed_nodes,
            summary=succeeded_summary,
        )

    async def run_index_job_with_artifacts(
        self,
        command: RunIndexJobCommand,
    ) -> RunIndexJobResult:
        self._ensure_persistence_configured()

        source = await self._get_source_or_raise(command.source_id)
        run: IndexPipelineRunRecord | None = None
        try:
            self._ensure_artifact_storage_configured()
            pipeline = await self.create_pipeline_run(
                CreateIndexPipelineRunCommand(
                    source_id=command.source_id,
                    parser=command.parser,
                    parser_config=command.parser_config,
                    chunker=command.chunker,
                    chunk_config=command.chunk_config,
                )
            )
            run = pipeline.run
            run = await self._execute_all_pipeline_stages(run=run, source=source)
            result = await self._run_index_result_from_pipeline(run=run, source=source)
            return replace(
                result,
                pipeline_run=run,
                artifact_capture_status="succeeded",
                artifact_capture_error=None,
            )
        except Exception as exc:
            failed_run = (
                await self._mark_pipeline_run_failed(run.run_id, str(exc))
                if run is not None
                else None
            )
            fallback = await self.run_index_job(command)
            return replace(
                fallback,
                pipeline_run=failed_run,
                artifact_capture_status="failed",
                artifact_capture_error=str(exc),
            )

    async def get_index_job(self, job_id: str) -> IndexJobRecord:
        self._ensure_persistence_configured()

        async with self._unit_of_work_factory() as uow:
            job = await uow.jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"Index job not found: {job_id}")
            return job

    async def get_indexing_artifacts(self, job_id: str) -> IndexingArtifactsResult:
        self._ensure_persistence_configured()

        async with self._unit_of_work_factory() as uow:
            job = await uow.jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"Index job not found: {job_id}")
            blocks = await uow.blocks.list_by_job(job_id)
            nodes = await uow.nodes.list_by_job(job_id)
            return IndexingArtifactsResult(job=job, blocks=blocks, nodes=nodes)

    async def _get_pipeline_run_or_raise(self, run_id: str) -> IndexPipelineRunRecord:
        async with self._unit_of_work_factory() as uow:
            run = await uow.pipeline_runs.get(run_id)
            if run is None:
                raise NotFoundError(f"Index pipeline run not found: {run_id}")
            return run

    async def _ensure_stage_dependencies(self, run_id: str, stage: IndexingStage) -> None:
        stage_index = INDEXING_STAGE_ORDER.index(stage)
        if stage_index == 0:
            return

        async with self._unit_of_work_factory() as uow:
            for dependency in INDEXING_STAGE_ORDER[:stage_index]:
                latest = await uow.stage_runs.latest_for_stage(
                    run_id=run_id,
                    stage_name=dependency,
                )
                if (
                    latest is None
                    or latest.status != IndexStageStatus.SUCCEEDED
                    or latest.stale
                ):
                    raise InvalidRequestError(
                        f"Stage '{stage.value}' requires fresh successful "
                        f"'{dependency.value}' artifacts."
                    )

    async def _start_stage_run(
        self,
        run: IndexPipelineRunRecord,
        stage: IndexingStage,
    ) -> IndexStageRunRecord:
        now = datetime.now(UTC)
        async with self._unit_of_work_factory() as uow:
            latest_stage = await uow.stage_runs.latest_for_stage(
                run_id=run.run_id,
                stage_name=stage,
            )
            if latest_stage is not None and latest_stage.status == IndexStageStatus.PENDING:
                stage_run = replace(
                    latest_stage,
                    status=IndexStageStatus.RUNNING,
                    stale=False,
                    started_at=now,
                    finished_at=None,
                    error_message=None,
                    duration_ms=None,
                    artifact_count=0,
                )
                stage_run = await uow.stage_runs.update(stage_run)
            else:
                sequence_no = (latest_stage.sequence_no + 1) if latest_stage else 1
                stage_run = await uow.stage_runs.create(
                    IndexStageRunRecord(
                        stage_run_id=f"stage_{uuid4().hex}",
                        run_id=run.run_id,
                        stage_name=stage,
                        status=IndexStageStatus.RUNNING,
                        sequence_no=sequence_no,
                        started_at=now,
                        created_at=now,
                    )
                )

            await uow.stage_runs.mark_stale_after(run_id=run.run_id, stage_name=stage)
            latest_run = await uow.pipeline_runs.get(run.run_id)
            if latest_run is None:
                raise NotFoundError(f"Index pipeline run not found: {run.run_id}")
            await uow.pipeline_runs.update(
                replace(
                    latest_run,
                    status=IndexPipelineStatus.RUNNING,
                    error_message=None,
                    started_at=latest_run.started_at or now,
                    finished_at=None,
                )
            )
            await uow.commit()
            return stage_run

    async def _execute_all_pipeline_stages(
        self,
        *,
        run: IndexPipelineRunRecord,
        source: SourceRecord,
    ) -> IndexPipelineRunRecord:
        current_run = run
        for stage in INDEXING_STAGE_ORDER:
            current_run, _, _ = await self._execute_pipeline_stage_once(
                run=current_run,
                source=source,
                stage=stage,
            )

        return current_run

    async def _execute_pipeline_stage_once(
        self,
        *,
        run: IndexPipelineRunRecord,
        source: SourceRecord,
        stage: IndexingStage,
    ) -> tuple[
        IndexPipelineRunRecord,
        IndexStageRunRecord,
        tuple[IndexArtifactManifestRecord, ...],
    ]:
        await self._ensure_stage_dependencies(run.run_id, stage)
        stage_run = await self._start_stage_run(run, stage)
        started_at = perf_counter()
        try:
            artifacts, summary, run_updates = await self._execute_pipeline_stage_payload(
                run=run,
                source=source,
                stage_run=stage_run,
                stage=stage,
            )
            manifests = tuple(
                _manifest_from_stored_artifact(
                    stored=stored,
                    run_id=run.run_id,
                    stage_run_id=stage_run.stage_run_id,
                    stage=stage,
                    artifact_type=artifact_type,
                )
                for artifact_type, stored in artifacts
            )
            success_updates = dict(run_updates)
            success_updates.setdefault("summary", summary)

            async with self._unit_of_work_factory() as uow:
                await uow.artifact_manifests.create_many(manifests)
                stage_run = await uow.stage_runs.update(
                    replace(
                        stage_run,
                        status=IndexStageStatus.SUCCEEDED,
                        summary=summary,
                        error_message=None,
                        finished_at=datetime.now(UTC),
                        duration_ms=_elapsed_ms(started_at),
                        artifact_count=len(manifests),
                    )
                )
                latest_run = await uow.pipeline_runs.get(run.run_id)
                if latest_run is None:
                    raise NotFoundError(f"Index pipeline run not found: {run.run_id}")
                updated_run = await uow.pipeline_runs.update(
                    _run_with_stage_success(latest_run, stage, success_updates)
                )
                await uow.commit()
                return updated_run, stage_run, manifests
        except Exception as exc:
            await self._mark_pipeline_stage_failed(
                run_id=run.run_id,
                stage_run=stage_run,
                error_message=str(exc),
                duration_ms=_elapsed_ms(started_at),
            )
            raise

    async def _execute_pipeline_stage_payload(
        self,
        *,
        run: IndexPipelineRunRecord,
        source: SourceRecord,
        stage_run: IndexStageRunRecord,
        stage: IndexingStage,
    ) -> tuple[list[tuple[str, Any]], dict[str, Any], dict[str, Any]]:
        if stage == IndexingStage.SOURCE:
            return self._write_source_stage_artifacts(run, source, stage_run), {
                "source_id": source.source_id,
                "filename": source.filename,
                "file_size": source.file_size,
                "has_file": source.file_path is not None,
            }, {}
        if stage == IndexingStage.PARSE_BLOCKS:
            return await self._execute_parse_stage(run, source, stage_run)
        if stage == IndexingStage.CHUNK_NODES:
            return await self._execute_chunk_stage(run, stage_run)
        if stage == IndexingStage.QUALITY_ENRICH:
            return await self._execute_quality_enrich_stage(run, stage_run)
        if stage == IndexingStage.VECTORIZE:
            return await self._execute_vectorize_stage(run, source, stage_run)
        raise InvalidRequestError(f"Unsupported indexing stage: {stage.value}")

    def _write_source_stage_artifacts(
        self,
        run: IndexPipelineRunRecord,
        source: SourceRecord,
        stage_run: IndexStageRunRecord,
    ) -> list[tuple[str, Any]]:
        payload = _source_record_artifact(source)
        stored = self._artifact_storage.write_json(
            source_id=source.source_id,
            run_id=run.run_id,
            stage_run_id=stage_run.stage_run_id,
            stage_name=IndexingStage.SOURCE.value,
            artifact_type="source_snapshot",
            payload=payload,
        )
        return [("source_snapshot", stored)]

    async def _execute_parse_stage(
        self,
        run: IndexPipelineRunRecord,
        source: SourceRecord,
        stage_run: IndexStageRunRecord,
    ) -> tuple[list[tuple[str, Any]], dict[str, Any], dict[str, Any]]:
        # 从config中获取parser配置
        parser_name = run.config.get("parser")
        parser_config = run.config.get("parser_config", {})

        resolved_parser = self._source_parser_registry.resolve(
            source=self._source_input_from_record(source),
            requested_parser=parser_name,
        )
        document = await resolved_parser.parser.parse(
            self._source_input_from_record(source),
            parser_config,
        )

        # VLM enhancement (optional)
        if self._modal_processor and self._should_enhance_with_vlm(document):
            document = await self._enhance_document_with_vlm(document)

        block_records = [_content_block_artifact(block) for block in document.blocks]
        document_payload = _source_document_artifact(document)
        stored_blocks = self._artifact_storage.write_jsonl(
            source_id=source.source_id,
            run_id=run.run_id,
            stage_run_id=stage_run.stage_run_id,
            stage_name=IndexingStage.PARSE_BLOCKS.value,
            artifact_type="blocks",
            records=block_records,
            compress=len(block_records) > 500,
        )
        stored_document = self._artifact_storage.write_json(
            source_id=source.source_id,
            run_id=run.run_id,
            stage_run_id=stage_run.stage_run_id,
            stage_name=IndexingStage.PARSE_BLOCKS.value,
            artifact_type="document",
            payload=document_payload,
        )
        summary = {
            "block_count": len(document.blocks),
            "page_count": document.page_count,
            "parser": resolved_parser.name,
            "parser_version": document.parser_version,
        }
        return (
            [("blocks", stored_blocks), ("document", stored_document)],
            summary,
            {},
        )

    async def _execute_chunk_stage(
        self,
        run: IndexPipelineRunRecord,
        stage_run: IndexStageRunRecord,
    ) -> tuple[list[tuple[str, Any]], dict[str, Any], dict[str, Any]]:
        document = await self._document_from_latest_artifacts(run.run_id)

        # 从config中获取chunker配置
        chunker_name = run.config.get("chunker")
        chunk_config = run.config.get("chunk_config", {})

        chunker = self._chunkers.get(chunker_name)
        if chunker is None:
            raise ConfigurationError(
                f"Chunker '{chunker_name}' is not registered."
            )

        # 创建tokenizer用于精确的Token级别处理
        tokenizer = self._create_tokenizer(
            chunk_config.get("tokenizer_model", "cl100k_base")
        )

        # 传递config和tokenizer给chunker
        nodes = tuple(chunker.chunk(document, chunk_config, tokenizer))

        # 在node metadata中添加tokenizer信息
        nodes = tuple(
            replace(node, metadata={**node.metadata, "tokenizer_model": tokenizer.model_name})
            for node in nodes
        )

        stored = self._artifact_storage.write_jsonl(
            source_id=document.source_id,
            run_id=run.run_id,
            stage_run_id=stage_run.stage_run_id,
            stage_name=IndexingStage.CHUNK_NODES.value,
            artifact_type="raw_nodes",
            records=[_index_node_artifact(node) for node in nodes],
            compress=len(nodes) > 500,
        )
        summary = {
            "node_count": len(nodes),
            "chunker": chunker_name,
            "chunk_size": chunk_config.get("chunk_size"),
            "chunk_overlap": chunk_config.get("chunk_overlap"),
            "tokenizer_model": tokenizer.model_name,
        }
        return [("raw_nodes", stored)], summary, {}

    async def _execute_quality_enrich_stage(
        self,
        run: IndexPipelineRunRecord,
        stage_run: IndexStageRunRecord,
    ) -> tuple[list[tuple[str, Any]], dict[str, Any], dict[str, Any]]:
        document = await self._document_from_latest_artifacts(run.run_id)
        chunk_config = run.config.get("chunk_config", {})
        raw_nodes = await self._nodes_from_latest_artifacts(
            run.run_id,
            IndexingStage.CHUNK_NODES,
            "raw_nodes",
        )
        # NodeEnricher不再需要profile，传递chunk_config
        enriched_nodes = tuple(self._node_enricher.enrich(raw_nodes, document, chunk_config))
        quality_metrics = calculate_chunk_quality(
            nodes=enriched_nodes,
            blocks=document.blocks,
            chunk_config=chunk_config,
            thresholds=QualityThresholds(),
        )
        summary = IndexingSummary.from_nodes(
            blocks=document.blocks,
            page_count=document.page_count,
            nodes=enriched_nodes,
            quality_metrics=quality_metrics,
        )
        stored_nodes = self._artifact_storage.write_jsonl(
            source_id=document.source_id,
            run_id=run.run_id,
            stage_run_id=stage_run.stage_run_id,
            stage_name=IndexingStage.QUALITY_ENRICH.value,
            artifact_type="enriched_nodes",
            records=[_index_node_artifact(node) for node in enriched_nodes],
            compress=len(enriched_nodes) > 500,
        )
        stored_quality = self._artifact_storage.write_json(
            source_id=document.source_id,
            run_id=run.run_id,
            stage_run_id=stage_run.stage_run_id,
            stage_name=IndexingStage.QUALITY_ENRICH.value,
            artifact_type="quality_report",
            payload=asdict(summary),
        )
        return (
            [("enriched_nodes", stored_nodes), ("quality_report", stored_quality)],
            asdict(summary),
            {"summary": asdict(summary)},
        )

    async def _execute_vectorize_stage(
        self,
        run: IndexPipelineRunRecord,
        source: SourceRecord,
        stage_run: IndexStageRunRecord,
    ) -> tuple[list[tuple[str, Any]], dict[str, Any], dict[str, Any]]:
        document = await self._document_from_latest_artifacts(run.run_id)
        enriched_nodes = await self._nodes_from_latest_artifacts(
            run.run_id,
            IndexingStage.QUALITY_ENRICH,
            "enriched_nodes",
        )

        # 固定collection名称
        COLLECTION_NAME = "ragmax_text_nodes"

        vector_started_at = perf_counter()
        indexed_nodes, vector_status, vector_count = await self._index_vectors_if_enabled(
            nodes=enriched_nodes,
            collection_name=COLLECTION_NAME,
        )
        vector_ms = _elapsed_ms(vector_started_at)
        persisted_summary = await self._persist_pipeline_latest_index(
            run=run,
            source=source,
            document=document,
            nodes=indexed_nodes,
            collection_name=COLLECTION_NAME,
            vector_status=vector_status,
            vector_count=vector_count,
            vector_ms=vector_ms,
        )
        payload = {
            "status": vector_status,
            "embedding_model": self._embedding_provider.model_name
            if self._embedding_provider is not None
            else None,
            "collection": COLLECTION_NAME
            if vector_status == "succeeded"
            else None,
            "vectorized_node_ids": [
                node.node_id
                for node in indexed_nodes
                if node.metadata.get("vector_point_id") is not None
            ],
            "node_count": len(indexed_nodes),
            "vectorized_count": vector_count,
            "vector_ms": vector_ms,
        }
        stored = self._artifact_storage.write_json(
            source_id=source.source_id,
            run_id=run.run_id,
            stage_run_id=stage_run.stage_run_id,
            stage_name=IndexingStage.VECTORIZE.value,
            artifact_type="vectorize_result",
            payload=payload,
        )
        return [("vectorize_result", stored)], payload, {
            "summary": persisted_summary,
            "status": IndexPipelineStatus.SUCCEEDED,
        }

    async def _document_from_latest_artifacts(self, run_id: str) -> SourceDocument:
        manifests = await self._latest_artifacts_by_stage(run_id, IndexingStage.PARSE_BLOCKS)
        document_manifest = _find_manifest(manifests, "document")
        blocks_manifest = _find_manifest(manifests, "blocks")
        document_payload = self._artifact_storage.read_json(document_manifest.storage_uri)
        block_records, _ = self._artifact_storage.read_jsonl(
            blocks_manifest.storage_uri,
            offset=0,
            limit=max(blocks_manifest.record_count, 1),
        )
        return _source_document_from_artifacts(document_payload, block_records)

    async def _nodes_from_latest_artifacts(
        self,
        run_id: str,
        stage: IndexingStage,
        artifact_type: str,
    ) -> tuple[IndexNode, ...]:
        manifests = await self._latest_artifacts_by_stage(run_id, stage)
        nodes_manifest = _find_manifest(manifests, artifact_type)
        node_records, _ = self._artifact_storage.read_jsonl(
            nodes_manifest.storage_uri,
            offset=0,
            limit=max(nodes_manifest.record_count, 1),
        )
        return tuple(_index_node_from_artifact(record) for record in node_records)

    async def _latest_artifacts_by_stage(
        self,
        run_id: str,
        stage: IndexingStage,
    ) -> tuple[IndexArtifactManifestRecord, ...]:
        async with self._unit_of_work_factory() as uow:
            manifests = await uow.artifact_manifests.list_latest_by_run_stage(
                run_id=run_id,
                stage_name=stage,
            )
            if not manifests:
                raise InvalidRequestError(
                    f"Stage '{stage.value}' has no artifacts for run '{run_id}'."
                )
            return manifests

    async def _persist_pipeline_latest_index(
        self,
        *,
        run: IndexPipelineRunRecord,
        source: SourceRecord,
        document: SourceDocument,
        nodes: tuple[IndexNode, ...],
        collection_name: str,
        vector_status: str,
        vector_count: int,
        vector_ms: float,
    ) -> dict[str, Any]:
        summary = IndexingSummary.from_nodes(
            blocks=document.blocks,
            page_count=document.page_count,
            nodes=nodes,
            vectorized_count=vector_count,
            performance={"vector_ms": vector_ms},
        )
        summary_dict = asdict(summary)
        summary_dict["vector_index"] = {
            "status": vector_status,
            "embedding_model": self._embedding_provider.model_name
            if self._embedding_provider is not None
            else None,
            "node_count": vector_count,
            "collection": collection_name if vector_status == "succeeded" else None,
        }

        # 从run.config提取配置信息
        chunker = run.config.get("chunker", "unknown")
        parser = run.config.get("parser", "unknown")

        job = IndexJobRecord(
            job_id=f"job_{uuid4().hex}",
            source_id=source.source_id,
            status=IndexJobStatus.SUCCEEDED,
            requested_chunker=chunker,
            effective_chunker=chunker,
            requested_parser=parser,
            effective_parser=parser,
            config=run.config,
            summary=summary_dict,
            vector_status=vector_status,
            node_count=len(nodes),
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        async with self._unit_of_work_factory() as uow:
            job = await uow.jobs.create(job)
            await uow.blocks.replace_for_source(
                source_id=source.source_id,
                job_id=job.job_id,
                blocks=_index_block_records_from_document(
                    job_id=job.job_id,
                    document=document,
                ),
            )
            await uow.nodes.replace_for_source(
                source_id=source.source_id,
                job_id=job.job_id,
                nodes=nodes,
            )
            await uow.commit()
        return {**summary_dict, "job_id": job.job_id}

    async def _run_index_result_from_pipeline(
        self,
        *,
        run: IndexPipelineRunRecord,
        source: SourceRecord,
    ) -> RunIndexJobResult:
        job_id = run.summary.get("job_id")
        if not isinstance(job_id, str) or not job_id:
            raise InvalidRequestError(
                f"Pipeline run '{run.run_id}' did not persist an index job."
            )

        async with self._unit_of_work_factory() as uow:
            job = await uow.jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"Index job not found: {job_id}")
            nodes = await uow.nodes.list_by_job(job_id)

        return RunIndexJobResult(
            job=job,
            source=source,
            effective_parser=job.effective_parser or str(run.config.get("parser") or ""),
            effective_chunker=job.effective_chunker or str(run.config.get("chunker") or ""),
            effective_config=job.config,
            nodes=nodes,
            summary=_summary_from_payload(job.summary),
            pipeline_run=run,
            artifact_capture_status="succeeded",
            artifact_capture_error=None,
        )

    async def _mark_pipeline_stage_failed(
        self,
        *,
        run_id: str,
        stage_run: IndexStageRunRecord,
        error_message: str,
        duration_ms: float,
    ) -> IndexPipelineRunRecord:
        async with self._unit_of_work_factory() as uow:
            await uow.stage_runs.update(
                replace(
                    stage_run,
                    status=IndexStageStatus.FAILED,
                    error_message=error_message,
                    finished_at=datetime.now(UTC),
                    duration_ms=duration_ms,
                )
            )
            run = await uow.pipeline_runs.get(run_id)
            if run is None:
                raise NotFoundError(f"Index pipeline run not found: {run_id}")
            failed_run = await uow.pipeline_runs.update(
                replace(
                    run,
                    status=IndexPipelineStatus.FAILED,
                    error_message=error_message,
                    finished_at=datetime.now(UTC),
                )
            )
            await uow.commit()
            return failed_run

    async def _mark_pipeline_run_failed(
        self,
        run_id: str,
        error_message: str,
    ) -> IndexPipelineRunRecord | None:
        async with self._unit_of_work_factory() as uow:
            run = await uow.pipeline_runs.get(run_id)
            if run is None:
                return None
            failed_run = await uow.pipeline_runs.update(
                replace(
                    run,
                    status=IndexPipelineStatus.FAILED,
                    error_message=error_message,
                    finished_at=datetime.now(UTC),
                )
            )
            await uow.commit()
            return failed_run

    async def get_source_for_indexing(self, source_id: str) -> SourceInput:
        source = await self._get_source_or_raise(source_id)
        return self._source_input_from_record(source)

    async def get_source(self, source_id: str) -> SourceRecord:
        return await self._get_source_or_raise(source_id)

    async def list_sources(self, limit: int = 100, offset: int = 0) -> tuple[SourceRecord, ...]:
        self._ensure_persistence_configured()
        async with self._unit_of_work_factory() as uow:
            return await uow.sources.list(limit=limit, offset=offset)

    async def delete_source(self, source_id: str) -> bool:
        self._ensure_persistence_configured()
        await self._get_source_or_raise(source_id)
        # Delete associated index data first
        await self.delete_source_index(source_id)
        # Delete pipeline runs
        async with self._unit_of_work_factory() as uow:
            # Pipeline runs will cascade delete due to foreign key
            deleted = await uow.sources.delete(source_id)
            await uow.commit()
        if deleted:
            await self._delete_source_files_if_enabled(source_id)
            await self._delete_artifacts_if_enabled(source_id)
        return deleted

    async def list_source_nodes(self, source_id: str) -> tuple[IndexNode, ...]:
        self._ensure_persistence_configured()
        await self._get_source_or_raise(source_id)

        async with self._unit_of_work_factory() as uow:
            return await uow.nodes.list_by_source(source_id)

    async def delete_source_index(self, source_id: str) -> DeleteSourceIndexResult:
        self._ensure_persistence_configured()
        await self._get_source_or_raise(source_id)
        vector_deleted_count = await self._delete_vectors_if_enabled(source_id)

        async with self._unit_of_work_factory() as uow:
            await uow.blocks.delete_by_source(source_id)
            deleted_count = await uow.nodes.delete_by_source(source_id)
            await uow.commit()
            return DeleteSourceIndexResult(
                source_id=source_id,
                deleted_count=deleted_count,
                vector_deleted_count=vector_deleted_count,
            )

    async def _index_vectors_if_enabled(
        self,
        *,
        nodes: tuple[IndexNode, ...],
        collection_name: str,
    ) -> tuple[tuple[IndexNode, ...], str, int]:
        if self._embedding_provider is None or self._vector_index_writer is None:
            return nodes, "skipped", 0

        vector_nodes = tuple(node for node in nodes if _is_vector_indexable_node(node))
        if not vector_nodes:
            return nodes, "skipped", 0

        embeddings = await self._embedding_provider.embed_texts(
            [node.text for node in vector_nodes]
        )
        if len(embeddings) != len(vector_nodes):
            raise ConfigurationError("Embedding provider returned an unexpected batch size.")

        vector_status = "failed"
        vector_records = await self._vector_index_writer.upsert_nodes(
            collection_name=collection_name,
            nodes=vector_nodes,
            embeddings=embeddings,
            embedding_model=self._embedding_provider.model_name,
        )
        vector_status = "succeeded"
        records_by_node_id = {record.node_id: record for record in vector_records}
        updated_nodes: list[IndexNode] = []
        for node in nodes:
            vector_record = records_by_node_id.get(node.node_id)
            if vector_record is None:
                updated_nodes.append(node)
                continue

            metadata = dict(node.metadata)
            metadata.update(
                {
                    "vector_collection": vector_record.collection_name,
                    "vector_point_id": vector_record.point_id,
                }
            )
            updated_nodes.append(
                replace(
                    node,
                    embedding_model=self._embedding_provider.model_name,
                    metadata=metadata,
                )
            )

        return tuple(updated_nodes), vector_status, len(vector_records)

    async def _delete_vectors_if_enabled(self, source_id: str) -> int:
        if self._vector_index_writer is None:
            return 0

        # 固定collection名称
        COLLECTION_NAME = "ragmax_text_nodes"
        deleted_count = await self._vector_index_writer.delete_source(
                collection_name=COLLECTION_NAME,
                source_id=source_id,
            )
        return deleted_count

    async def _delete_source_files_if_enabled(self, source_id: str) -> None:
        if self._source_storage is None:
            return
        try:
            await self._source_storage.delete_source(source_id)
        except Exception:
            logger.warning(
                "Failed to delete source files for source_id=%s",
                source_id,
                exc_info=True,
            )

    async def _delete_artifacts_if_enabled(self, source_id: str) -> None:
        if self._artifact_storage is None:
            return
        delete_source = getattr(self._artifact_storage, "delete_source", None)
        if delete_source is None:
            return
        try:
            await delete_source(source_id)
        except Exception:
            logger.warning(
                "Failed to delete indexing artifacts for source_id=%s",
                source_id,
                exc_info=True,
            )

    async def _build_preview(self, command: PreviewIndexingCommand) -> PreviewIndexingResult:
        from ragmax.core.defaults import (
            DEFAULT_CHUNKER,
            get_default_chunk_config,
            get_default_parser,
        )

        # 解析配置
        parser_name = command.parser or get_default_parser(command.source.media_type)
        parser_config = command.parser_config or {}
        chunker_name = command.chunker or DEFAULT_CHUNKER
        chunk_config = command.chunk_config or get_default_chunk_config(chunker_name)

        resolved_parser = self._source_parser_registry.resolve(
            source=command.source,
            requested_parser=parser_name,
        )

        started_at = perf_counter()
        parse_started_at = perf_counter()
        document = await resolved_parser.parser.parse(command.source, parser_config)
        parse_ms = _elapsed_ms(parse_started_at)

        # VLM enhancement (optional)
        if self._modal_processor and self._should_enhance_with_vlm(document):
            document = await self._enhance_document_with_vlm(document)

        chunker = self._chunkers.get(chunker_name)
        if chunker is None:
            raise ConfigurationError(
                f"Chunker '{chunker_name}' is not registered."
            )

        chunk_started_at = perf_counter()
        tokenizer = self._create_tokenizer(chunk_config.get("tokenizer_model", "cl100k_base"))
        nodes = chunker.chunk(document, chunk_config, tokenizer)
        chunk_ms = _elapsed_ms(chunk_started_at)

        enrich_started_at = perf_counter()
        enriched_nodes = tuple(self._node_enricher.enrich(nodes, document, chunk_config))
        enrich_ms = _elapsed_ms(enrich_started_at)

        # Calculate chunk quality metrics
        quality_started_at = perf_counter()
        quality_metrics = calculate_chunk_quality(
            nodes=enriched_nodes,
            blocks=document.blocks,
            chunk_config=chunk_config,
            thresholds=QualityThresholds(),
        )
        quality_ms = _elapsed_ms(quality_started_at)

        summary = IndexingSummary.from_nodes(
            blocks=document.blocks,
            page_count=document.page_count,
            nodes=enriched_nodes,
            performance={
                "parse_ms": parse_ms,
                "chunk_ms": chunk_ms,
                "enrich_ms": enrich_ms,
                "quality_ms": quality_ms,
                "preview_total_ms": _elapsed_ms(started_at),
            },
            quality_metrics=quality_metrics,
        )

        return PreviewIndexingResult(
            effective_parser=resolved_parser.name,
            effective_chunker=chunker_name,
            effective_config={
                "parser": parser_name,
                "parser_config": parser_config,
                "chunker": chunker_name,
                "chunk_config": chunk_config,
            },
            document=document,
            nodes=enriched_nodes,
            summary=summary,
        )

    async def _get_source_or_raise(self, source_id: str) -> SourceRecord:
        async with self._unit_of_work_factory() as uow:
            source = await uow.sources.get(source_id)
            if source is None:
                raise NotFoundError(f"Source not found: {source_id}")
            return source

    def _source_input_from_record(self, source: SourceRecord) -> SourceInput:
        return SourceInput(
            source_id=source.source_id,
            notebook_id=source.notebook_id,
            filename=source.filename,
            media_type=source.media_type,
            text=source.text,
            file_path=source.file_path,
            file_size=source.file_size,
            input_blocks=tuple(
                SourceInputBlock(
                    block_id=block.get("block_id"),
                    block_type=block.get("block_type", "text"),
                    text=block.get("text", ""),
                    page_no=block.get("page_no"),
                    bbox=tuple(block["bbox"]) if block.get("bbox") else None,
                    section_hint=tuple(block.get("section_hint", ())),
                    metadata=dict(block.get("metadata", {})),
                )
                for block in source.input_blocks
            ),
            metadata=source.metadata,
        )

    def _ensure_persistence_configured(self) -> None:
        if self._unit_of_work_factory is None:
            raise ConfigurationError("Indexing persistence is not configured.")

    def _ensure_artifact_storage_configured(self) -> None:
        if self._artifact_storage is None:
            raise ConfigurationError("Indexing artifact storage is not configured.")

    def _build_source_hash(
        self,
        text: str | None,
        blocks: tuple[SourceInputBlock, ...],
        *,
        provided_hash: str | None = None,
    ) -> str:
        if provided_hash:
            return provided_hash
        payload = {
            "text": text,
            "input_blocks": [asdict(block) for block in blocks],
        }
        encoded_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded_payload).hexdigest()

    def _should_enhance_with_vlm(self, document: SourceDocument) -> bool:
        """Check if document has multimodal content worth enhancing."""
        from ragmax.domain.indexing.blocks import BlockType
        multimodal_types = {BlockType.IMAGE, BlockType.TABLE, BlockType.EQUATION}
        return any(block.block_type in multimodal_types for block in document.blocks)

    async def _enhance_document_with_vlm(self, document: SourceDocument) -> SourceDocument:
        """Enhance multimodal blocks with VLM analysis."""
        from ragmax.domain.indexing.context import ContextConfig, ContextExtractor

        context_extractor = ContextExtractor()
        config = ContextConfig(
            context_window=1,
            context_mode="page",
            max_context_tokens=2000,
            include_headers=True,
            include_captions=True,
        )

        enhanced_blocks = []
        for idx, block in enumerate(document.blocks):
            from ragmax.domain.indexing.blocks import BlockType
            if block.block_type not in {BlockType.IMAGE, BlockType.TABLE}:
                enhanced_blocks.append(block)
                continue

            context = context_extractor.extract_context(
                blocks=document.blocks,
                current_index=idx,
                config=config,
            )

            try:
                enhanced_block = await self._modal_processor.process_block(
                    block=block,
                    context=context,
                    section_path=block.section_hint,
                )
                enhanced_blocks.append(enhanced_block)
            except Exception as exc:
                logger.warning(
                    "VLM enhancement failed for block %s: %s",
                    block.block_id,
                    exc,
                    exc_info=True,
                )
                enhanced_blocks.append(block)

        return replace(document, blocks=tuple(enhanced_blocks))


def _is_vector_indexable_node(node: IndexNode) -> bool:
    if node.modality != "text" or not node.text.strip():
        return False
    return _node_role(node) != "parent"


def _node_role(node: IndexNode) -> str:
    if node.parent_node_id:
        return "child"
    if node.content_type == "section":
        return "parent"
    return "leaf"


def _index_block_records_from_document(
    *,
    job_id: str,
    document,
) -> tuple[IndexBlockRecord, ...]:
    return tuple(
        _index_block_record_from_content_block(
            job_id=job_id,
            notebook_id=document.notebook_id,
            parser_name=document.parser_name,
            parser_version=document.parser_version,
            order_index=index,
            block=block,
        )
        for index, block in enumerate(document.blocks, start=1)
    )


def _index_block_record_from_content_block(
    *,
    job_id: str,
    notebook_id: str,
    parser_name: str,
    parser_version: str,
    order_index: int,
    block: ContentBlock,
) -> IndexBlockRecord:
    return IndexBlockRecord(
        block_id=block.block_id,
        job_id=job_id,
        source_id=block.source_id,
        notebook_id=notebook_id,
        order_index=order_index,
        block_type=block.block_type,
        text=block.text,
        page_no=block.page_no,
        bbox=block.bbox,
        section_hint=block.section_hint,
        parser_name=parser_name,
        parser_version=parser_version,
        content_hash=hashlib.sha256(block.normalized_text.encode("utf-8")).hexdigest(),
        metadata=dict(block.metadata),
    )


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 3)


def _parse_stage(stage_name: str) -> IndexingStage:
    try:
        return IndexingStage(stage_name)
    except ValueError as exc:
        supported = ", ".join(stage.value for stage in INDEXING_STAGE_ORDER)
        raise InvalidRequestError(
            f"Unsupported indexing stage '{stage_name}'. Supported stages: {supported}."
        ) from exc


def _manifest_from_stored_artifact(
    *,
    stored: Any,
    run_id: str,
    stage_run_id: str,
    stage: IndexingStage,
    artifact_type: str,
) -> IndexArtifactManifestRecord:
    return IndexArtifactManifestRecord(
        artifact_id=f"artifact_{uuid4().hex}",
        run_id=run_id,
        stage_run_id=stage_run_id,
        stage_name=stage,
        artifact_type=artifact_type,
        storage_uri=stored.storage_uri,
        payload_format=stored.payload_format,
        content_hash=stored.sha256,
        size_bytes=stored.size_bytes,
        record_count=stored.record_count,
        preview=stored.preview,
        created_at=datetime.now(UTC),
    )


def _run_with_stage_success(
    run: IndexPipelineRunRecord,
    stage: IndexingStage,
    updates: dict[str, Any],
) -> IndexPipelineRunRecord:
    summary = dict(run.summary or {})
    stage_summaries = dict(summary.get("stages") or {})
    if "summary" in updates and isinstance(updates["summary"], dict):
        stage_summaries[stage.value] = updates["summary"]
    summary["stages"] = stage_summaries
    if stage == IndexingStage.VECTORIZE and isinstance(updates.get("summary"), dict):
        summary.update(updates["summary"])

    status = updates.get("status")
    if not isinstance(status, IndexPipelineStatus):
        status = IndexPipelineStatus.RUNNING

    return replace(
        run,
        status=status,
        config={**run.config, **dict(updates.get("config") or {})},
        summary=summary,
        error_message=None,
        finished_at=datetime.now(UTC) if status == IndexPipelineStatus.SUCCEEDED else None,
    )


def _source_record_artifact(source: SourceRecord) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "notebook_id": source.notebook_id,
        "filename": source.filename,
        "media_type": source.media_type,
        "source_hash": source.source_hash,
        "has_file": source.file_path is not None,
        "file_size": source.file_size,
        "metadata": source.metadata,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None,
    }


def _source_document_artifact(document: SourceDocument) -> dict[str, Any]:
    return {
        "source_id": document.source_id,
        "notebook_id": document.notebook_id,
        "filename": document.filename,
        "media_type": document.media_type,
        "parser_name": document.parser_name,
        "parser_version": document.parser_version,
        "page_count": document.page_count,
        "metadata": document.metadata,
    }


def _content_block_artifact(block: ContentBlock) -> dict[str, Any]:
    return {
        "block_id": block.block_id,
        "source_id": block.source_id,
        "block_type": block.block_type.value,
        "text": block.text,
        "page_no": block.page_no,
        "bbox": list(block.bbox) if block.bbox else None,
        "section_hint": list(block.section_hint),
        "metadata": block.metadata,
    }


def _content_block_from_artifact(payload: dict[str, Any]) -> ContentBlock:
    from ragmax.domain.indexing.blocks import BlockType

    bbox = tuple(payload["bbox"]) if payload.get("bbox") else None
    return ContentBlock(
        block_id=payload["block_id"],
        source_id=payload["source_id"],
        block_type=BlockType(payload["block_type"]),
        text=payload.get("text") or "",
        page_no=payload.get("page_no"),
        bbox=bbox,
        section_hint=tuple(payload.get("section_hint") or ()),
        metadata=dict(payload.get("metadata") or {}),
    )


def _source_document_from_artifacts(
    document_payload: dict[str, Any],
    block_records: list[dict[str, Any]],
) -> SourceDocument:
    return SourceDocument(
        source_id=document_payload["source_id"],
        notebook_id=document_payload["notebook_id"],
        filename=document_payload["filename"],
        media_type=document_payload["media_type"],
        parser_name=document_payload["parser_name"],
        parser_version=document_payload["parser_version"],
        blocks=tuple(_content_block_from_artifact(record) for record in block_records),
        metadata=dict(document_payload.get("metadata") or {}),
    )


def _index_node_artifact(node: IndexNode) -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "source_id": node.source_id,
        "notebook_id": node.notebook_id,
        "text": node.text,
        "modality": node.modality,
        "content_type": node.content_type,
        "page_start": node.page_start,
        "page_end": node.page_end,
        "section_path": list(node.section_path),
        "block_ids": list(node.block_ids),
        "parent_node_id": node.parent_node_id,
        "asset_path": node.asset_path,
        "bbox": list(node.bbox) if node.bbox else None,
        "indexing_profile": node.indexing_profile,
        "parser_version": node.parser_version,
        "chunker_version": node.chunker_version,
        "embedding_model": node.embedding_model,
        "metadata": node.metadata,
    }


def _index_node_from_artifact(payload: dict[str, Any]) -> IndexNode:
    bbox = tuple(payload["bbox"]) if payload.get("bbox") else None
    return IndexNode(
        node_id=payload["node_id"],
        source_id=payload["source_id"],
        notebook_id=payload["notebook_id"],
        text=payload.get("text") or "",
        modality=payload.get("modality") or "text",
        content_type=payload.get("content_type") or "text",
        page_start=payload.get("page_start"),
        page_end=payload.get("page_end"),
        section_path=tuple(payload.get("section_path") or ()),
        block_ids=tuple(payload.get("block_ids") or ()),
        parent_node_id=payload.get("parent_node_id"),
        asset_path=payload.get("asset_path"),
        bbox=bbox,
        indexing_profile=payload.get("indexing_profile"),
        parser_version=payload.get("parser_version"),
        chunker_version=payload.get("chunker_version"),
        embedding_model=payload.get("embedding_model"),
        metadata=dict(payload.get("metadata") or {}),
    )




def _summary_from_payload(payload: dict[str, Any]) -> IndexingSummary:
    return IndexingSummary(
        block_count=int(payload.get("block_count") or 0),
        node_count=int(payload.get("node_count") or 0),
        page_count=int(payload.get("page_count") or 0),
        block_types=dict(payload.get("block_types") or {}),
        content_types=dict(payload.get("content_types") or {}),
        modalities=dict(payload.get("modalities") or {}),
        node_roles=dict(payload.get("node_roles") or {}),
        vectorized_count=int(payload.get("vectorized_count") or 0),
        chunk_length_stats=dict(payload.get("chunk_length_stats") or {}),
        quality=dict(payload.get("quality") or {}),
        performance=dict(payload.get("performance") or {}),
    )


def _find_manifest(
    manifests: tuple[IndexArtifactManifestRecord, ...],
    artifact_type: str,
) -> IndexArtifactManifestRecord:
    for manifest in manifests:
        if manifest.artifact_type == artifact_type:
            return manifest
    raise InvalidRequestError(f"Artifact '{artifact_type}' is not available.")
