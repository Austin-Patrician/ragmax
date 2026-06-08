import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, replace
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from ragmax.application.indexing.dtos import (
    CreateSourceCommand,
    DeleteSourceIndexResult,
    IndexingArtifactsResult,
    PreviewIndexingCommand,
    PreviewIndexingResult,
    RunIndexJobCommand,
    RunIndexJobResult,
    SourceInput,
    SourceInputBlock,
)
from ragmax.application.indexing.parser_registry import SourceParserRegistry
from ragmax.application.indexing.ports import (
    EmbeddingProvider,
    IndexingUnitOfWork,
    VectorIndexWriter,
)
from ragmax.application.indexing.registry import IndexingProfileRegistry
from ragmax.core.exceptions import ConfigurationError, NotFoundError
from ragmax.domain.indexing.analysis import IndexingSummary
from ragmax.domain.indexing.blocks import ContentBlock
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.ports import Chunker, NodeEnricher, SourceAnalyzer
from ragmax.domain.indexing.quality import calculate_chunk_quality, QualityThresholds
from ragmax.domain.indexing.records import (
    IndexBlockRecord,
    IndexJobRecord,
    IndexJobStatus,
    SourceRecord,
)

IndexingUnitOfWorkFactory = Callable[[], IndexingUnitOfWork]


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
    ) -> None:
        self._source_parser_registry = source_parser_registry
        self._source_analyzer = source_analyzer
        self._profile_registry = profile_registry
        self._chunkers = dict(chunkers)
        self._node_enricher = node_enricher
        self._embedding_provider = embedding_provider
        self._vector_index_writer = vector_index_writer
        self._unit_of_work_factory = unit_of_work_factory

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

    async def get_source_for_indexing(self, source_id: str) -> SourceInput:
        source = await self._get_source_or_raise(source_id)
        return self._source_input_from_record(source)

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
