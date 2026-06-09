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
from ragmax.application.indexing.registry import IndexingProfileRegistry
from ragmax.core.exceptions import ConfigurationError, InvalidRequestError, NotFoundError
from ragmax.domain.indexing.analysis import IndexingSummary
from ragmax.domain.indexing.blocks import ContentBlock
from ragmax.domain.indexing.documents import SourceDocument
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.ports import Chunker, NodeEnricher, SourceAnalyzer
from ragmax.domain.indexing.profiles import IndexingProfile, IndexingProfileName, NodeGraphMode
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

IndexingUnitOfWorkFactory = Callable[[], IndexingUnitOfWork]
logger = logging.getLogger(__name__)


class IndexingService:
    def __init__(
        self,
        *,
        source_parser_registry: SourceParserRegistry,
        source_analyzer: SourceAnalyzer,
        profile_registry: IndexingProfileRegistry,
        chunkers: Mapping[str, Chunker],
        node_enricher: NodeEnricher,
        embedding_provider: EmbeddingProvider | None = None,
        vector_index_writer: VectorIndexWriter | None = None,
        unit_of_work_factory: IndexingUnitOfWorkFactory | None = None,
        artifact_storage: Any | None = None,
        source_storage: Any | None = None,
    ) -> None:
        self._source_parser_registry = source_parser_registry
        self._source_analyzer = source_analyzer
        self._profile_registry = profile_registry
        self._chunkers = dict(chunkers)
        self._node_enricher = node_enricher
        self._embedding_provider = embedding_provider
        self._vector_index_writer = vector_index_writer
        self._unit_of_work_factory = unit_of_work_factory
        self._artifact_storage = artifact_storage
        self._source_storage = source_storage

    def list_profiles(self):
        return self._profile_registry.list()

    def list_parsers(self):
        return self._source_parser_registry.list()

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
        run = IndexPipelineRunRecord(
            run_id=f"run_{uuid4().hex}",
            source_id=source.source_id,
            status=IndexPipelineStatus.PENDING,
            requested_profile=command.profile_name,
            requested_parser=command.parser_name,
            overrides={
                "profile": asdict(command.overrides),
                "parser_options": command.parser_options,
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
            requested_profile=command.profile_name,
            requested_parser=command.parser_name,
            overrides={
                "profile": asdict(command.overrides),
                "parser_options": command.parser_options,
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
                    profile_name=command.profile_name,
                    parser_name=command.parser_name,
                    parser_options=command.parser_options,
                    overrides=command.overrides,
                )
            )
            vector_status = "running"
            vector_started_at = perf_counter()
            indexed_nodes, vector_status, vector_count = await self._index_vectors_if_enabled(
                nodes=preview_result.nodes,
                profile=preview_result.effective_profile,
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
            "collection": preview_result.effective_profile.text_collection
            if vector_status == "succeeded"
            else None,
        }
        succeeded_job = replace(
            job,
            status=IndexJobStatus.SUCCEEDED,
            effective_profile=preview_result.effective_profile.name.value,
            effective_parser=preview_result.effective_parser,
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
            effective_profile=preview_result.effective_profile,
            effective_parser=preview_result.effective_parser,
            nodes=indexed_nodes,
            summary=succeeded_summary,
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
        if stage == IndexingStage.ANALYZE_PROFILE:
            return await self._execute_analyze_stage(run, stage_run)
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
        resolved_parser = self._source_parser_registry.resolve(
            source=self._source_input_from_record(source),
            requested_parser=run.requested_parser,
        )
        parser_options = dict((run.overrides or {}).get("parser_options") or {})
        document = await resolved_parser.parser.parse(
            self._source_input_from_record(source),
            parser_options,
        )
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
            {"effective_parser": resolved_parser.name},
        )

    async def _execute_analyze_stage(
        self,
        run: IndexPipelineRunRecord,
        stage_run: IndexStageRunRecord,
    ) -> tuple[list[tuple[str, Any]], dict[str, Any], dict[str, Any]]:
        document = await self._document_from_latest_artifacts(run.run_id)
        analysis = self._source_analyzer.analyze(document, self._profile_registry.list())
        profile_name = run.requested_profile or analysis.recommended_profile.value
        effective_profile = self._profile_registry.resolve(
            profile_name,
            _profile_overrides_from_run(run),
        )
        payload = {
            "recommended_profile": analysis.recommended_profile.value,
            "reasons": list(analysis.reasons),
            "traits": analysis.traits,
            "effective_profile": effective_profile.to_dict(),
        }
        stored = self._artifact_storage.write_json(
            source_id=document.source_id,
            run_id=run.run_id,
            stage_run_id=stage_run.stage_run_id,
            stage_name=IndexingStage.ANALYZE_PROFILE.value,
            artifact_type="profile_analysis",
            payload=payload,
        )
        summary = {
            "recommended_profile": analysis.recommended_profile.value,
            "effective_profile": effective_profile.name.value,
            "reason_count": len(analysis.reasons),
        }
        return [("profile_analysis", stored)], summary, {
            "effective_profile": effective_profile.name.value
        }

    async def _execute_chunk_stage(
        self,
        run: IndexPipelineRunRecord,
        stage_run: IndexStageRunRecord,
    ) -> tuple[list[tuple[str, Any]], dict[str, Any], dict[str, Any]]:
        document = await self._document_from_latest_artifacts(run.run_id)
        effective_profile = await self._effective_profile_from_latest_artifacts(run.run_id)
        chunker = self._chunkers.get(effective_profile.chunker)
        if chunker is None:
            raise ConfigurationError(
                f"Chunker '{effective_profile.chunker}' is not registered for profile "
                f"'{effective_profile.name.value}'."
            )
        nodes = tuple(chunker.chunk(document, effective_profile))
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
            "chunker": effective_profile.chunker,
            "chunk_size": effective_profile.chunk_size,
            "chunk_overlap": effective_profile.chunk_overlap,
        }
        return [("raw_nodes", stored)], summary, {}

    async def _execute_quality_enrich_stage(
        self,
        run: IndexPipelineRunRecord,
        stage_run: IndexStageRunRecord,
    ) -> tuple[list[tuple[str, Any]], dict[str, Any], dict[str, Any]]:
        document = await self._document_from_latest_artifacts(run.run_id)
        effective_profile = await self._effective_profile_from_latest_artifacts(run.run_id)
        raw_nodes = await self._nodes_from_latest_artifacts(
            run.run_id,
            IndexingStage.CHUNK_NODES,
            "raw_nodes",
        )
        enriched_nodes = tuple(self._node_enricher.enrich(raw_nodes, document, effective_profile))
        quality_metrics = calculate_chunk_quality(
            nodes=enriched_nodes,
            blocks=document.blocks,
            profile=effective_profile,
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
        effective_profile = await self._effective_profile_from_latest_artifacts(run.run_id)
        enriched_nodes = await self._nodes_from_latest_artifacts(
            run.run_id,
            IndexingStage.QUALITY_ENRICH,
            "enriched_nodes",
        )
        vector_started_at = perf_counter()
        indexed_nodes, vector_status, vector_count = await self._index_vectors_if_enabled(
            nodes=enriched_nodes,
            profile=effective_profile,
        )
        vector_ms = _elapsed_ms(vector_started_at)
        persisted_summary = await self._persist_pipeline_latest_index(
            run=run,
            source=source,
            document=document,
            nodes=indexed_nodes,
            profile=effective_profile,
            vector_status=vector_status,
            vector_count=vector_count,
            vector_ms=vector_ms,
        )
        payload = {
            "status": vector_status,
            "embedding_model": self._embedding_provider.model_name
            if self._embedding_provider is not None
            else None,
            "collection": effective_profile.text_collection
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

    async def _effective_profile_from_latest_artifacts(self, run_id: str) -> IndexingProfile:
        manifests = await self._latest_artifacts_by_stage(run_id, IndexingStage.ANALYZE_PROFILE)
        analysis_manifest = _find_manifest(manifests, "profile_analysis")
        payload = self._artifact_storage.read_json(analysis_manifest.storage_uri)
        return _profile_from_payload(payload["effective_profile"])

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
        profile: IndexingProfile,
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
            "collection": profile.text_collection if vector_status == "succeeded" else None,
        }
        job = IndexJobRecord(
            job_id=f"job_{uuid4().hex}",
            source_id=source.source_id,
            status=IndexJobStatus.SUCCEEDED,
            requested_profile=run.requested_profile,
            effective_profile=profile.name.value,
            requested_parser=run.requested_parser,
            effective_parser=run.effective_parser,
            overrides=run.overrides,
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
        profile,
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
            collection_name=profile.text_collection,
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

        deleted_count = 0
        collection_names = {profile.text_collection for profile in self._profile_registry.list()}
        for collection_name in collection_names:
            deleted_count += await self._vector_index_writer.delete_source(
                collection_name=collection_name,
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
        if command.profile_name is not None:
            self._profile_registry.get(command.profile_name)
        resolved_parser = self._source_parser_registry.resolve(
            source=command.source,
            requested_parser=command.parser_name,
        )
        started_at = perf_counter()
        parse_started_at = perf_counter()
        document = await resolved_parser.parser.parse(command.source, command.parser_options)
        parse_ms = _elapsed_ms(parse_started_at)

        analyze_started_at = perf_counter()
        analysis = self._source_analyzer.analyze(document, self._profile_registry.list())
        analyze_ms = _elapsed_ms(analyze_started_at)

        profile_name = command.profile_name or analysis.recommended_profile.value
        effective_profile = self._profile_registry.resolve(profile_name, command.overrides)

        chunker = self._chunkers.get(effective_profile.chunker)
        if chunker is None:
            raise ConfigurationError(
                f"Chunker '{effective_profile.chunker}' is not registered for profile "
                f"'{effective_profile.name.value}'."
            )

        chunk_started_at = perf_counter()
        nodes = chunker.chunk(document, effective_profile)
        chunk_ms = _elapsed_ms(chunk_started_at)

        enrich_started_at = perf_counter()
        enriched_nodes = tuple(self._node_enricher.enrich(nodes, document, effective_profile))
        enrich_ms = _elapsed_ms(enrich_started_at)

        # Calculate chunk quality metrics
        quality_started_at = perf_counter()
        quality_metrics = calculate_chunk_quality(
            nodes=enriched_nodes,
            blocks=document.blocks,
            profile=effective_profile,
            thresholds=QualityThresholds(),
        )
        quality_ms = _elapsed_ms(quality_started_at)

        summary = IndexingSummary.from_nodes(
            blocks=document.blocks,
            page_count=document.page_count,
            nodes=enriched_nodes,
            performance={
                "parse_ms": parse_ms,
                "analyze_ms": analyze_ms,
                "chunk_ms": chunk_ms,
                "enrich_ms": enrich_ms,
                "quality_ms": quality_ms,
                "preview_total_ms": _elapsed_ms(started_at),
            },
            quality_metrics=quality_metrics,
        )

        return PreviewIndexingResult(
            analysis=analysis,
            effective_profile=effective_profile,
            effective_parser=resolved_parser.name,
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


def _profile_overrides_from_run(run: IndexPipelineRunRecord) -> Any:
    from ragmax.application.indexing.dtos import ProfileOverrides

    profile_overrides = dict((run.overrides or {}).get("profile") or {})
    return ProfileOverrides(
        chunk_size=profile_overrides.get("chunk_size"),
        chunk_overlap=profile_overrides.get("chunk_overlap"),
        options=dict(profile_overrides.get("options") or {}),
    )


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
        effective_profile=updates.get("effective_profile", run.effective_profile),
        effective_parser=updates.get("effective_parser", run.effective_parser),
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


def _profile_from_payload(payload: dict[str, Any]) -> IndexingProfile:
    return IndexingProfile(
        name=IndexingProfileName(payload["name"]),
        description=payload["description"],
        chunker=payload["chunker"],
        chunk_size=payload["chunk_size"],
        chunk_overlap=payload["chunk_overlap"],
        node_graph_mode=NodeGraphMode(payload["node_graph_mode"]),
        supported_media_types=tuple(payload.get("supported_media_types") or ()),
        text_collection=payload.get("text_collection") or "ragmax_text_nodes",
        visual_collection=payload.get("visual_collection") or "ragmax_visual_nodes",
        options=dict(payload.get("options") or {}),
    )


def _find_manifest(
    manifests: tuple[IndexArtifactManifestRecord, ...],
    artifact_type: str,
) -> IndexArtifactManifestRecord:
    for manifest in manifests:
        if manifest.artifact_type == artifact_type:
            return manifest
    raise InvalidRequestError(f"Artifact '{artifact_type}' is not available.")
