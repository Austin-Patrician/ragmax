from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from ragmax.api.auth_dependencies import ROUTE_INDEXING, require_route_permission
from ragmax.api.dependencies import get_indexing_service
from ragmax.application.indexing.dtos import (
    IndexArtifactDataResult,
    IndexPipelineRunResult,
    PreviewIndexingCommand,
    SourceInput,
    SourceInputBlock,
    StageArtifactsResult,
)
from ragmax.application.indexing.service import IndexingService
from ragmax.core.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidRequestError,
    NotFoundError,
)

router = APIRouter(
    prefix="/indexing",
    tags=["indexing"],
    dependencies=[Depends(require_route_permission(ROUTE_INDEXING))],
)


class SourceParserResponse(BaseModel):
    name: str
    description: str
    supported_extensions: list[str]
    supported_media_types: list[str]
    requires_api_key: bool
    is_default: bool
    is_internal: bool


class ContentBlockPayload(BaseModel):
    block_id: str | None = None
    block_type: str = "text"
    text: str = ""
    page_no: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    section_hint: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourcePayload(BaseModel):
    source_id: str = "preview-source"
    notebook_id: str = "preview-notebook"
    filename: str = "preview.txt"
    media_type: str = "text/plain"
    text: str | None = None
    blocks: list[ContentBlockPayload] = Field(default_factory=list)
    file_path: str | None = None
    file_size: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_content(self) -> SourcePayload:
        has_text = bool(self.text and self.text.strip())
        has_blocks = bool(self.blocks)
        has_file = bool(self.file_path)
        if not has_text and not has_blocks and not has_file:
            raise ValueError("Provide source.text, source.blocks, or source.file_path.")
        return self


class IndexingPreviewRequest(BaseModel):
    parser: str | None = None
    parser_config: dict[str, Any] = Field(default_factory=dict)
    chunker: str | None = None
    chunk_config: dict[str, Any] = Field(default_factory=dict)
    source: SourcePayload


class ContentBlockResponse(BaseModel):
    block_id: str
    source_id: str
    block_type: str
    text: str
    page_no: int | None
    bbox: tuple[float, float, float, float] | None
    section_hint: list[str]
    metadata: dict[str, Any]


class IndexBlockResponse(BaseModel):
    block_id: str
    job_id: str
    source_id: str
    notebook_id: str
    order_index: int
    block_type: str
    text: str
    page_no: int | None
    bbox: tuple[float, float, float, float] | None
    section_hint: list[str]
    parser_name: str | None
    parser_version: str | None
    content_hash: str | None
    metadata: dict[str, Any]


class IndexNodeResponse(BaseModel):
    node_id: str
    source_id: str
    notebook_id: str
    text: str
    modality: str
    content_type: str
    page_start: int | None
    page_end: int | None
    section_path: list[str]
    block_ids: list[str]
    parent_node_id: str | None
    asset_path: str | None
    bbox: tuple[float, float, float, float] | None
    indexing_profile: str | None
    parser_version: str | None
    chunker_version: str | None
    embedding_model: str | None
    metadata: dict[str, Any]


class IndexingSummaryResponse(BaseModel):
    block_count: int
    node_count: int
    page_count: int
    block_types: dict[str, int]
    content_types: dict[str, int]
    modalities: dict[str, int]
    node_roles: dict[str, int]
    vectorized_count: int
    chunk_length_stats: dict[str, int]
    quality: dict[str, Any]
    performance: dict[str, float]


class IndexJobResponse(BaseModel):
    job_id: str
    source_id: str
    status: str
    requested_chunker: str | None
    effective_chunker: str | None
    requested_parser: str | None
    effective_parser: str | None
    config: dict[str, Any]
    summary: dict[str, Any]
    error_message: str | None
    vector_status: str | None
    vector_error_message: str | None
    node_count: int


class IndexingPreviewResponse(BaseModel):
    effective_parser: str
    effective_chunker: str
    effective_config: dict[str, Any]
    blocks: list[ContentBlockResponse]
    nodes: list[IndexNodeResponse]
    summary: IndexingSummaryResponse


class IndexingArtifactsResponse(BaseModel):
    job: IndexJobResponse
    blocks: list[IndexBlockResponse]
    nodes: list[IndexNodeResponse]
    vectorized_node_ids: list[str]
    metrics: dict[str, Any]


class IndexArtifactManifestResponse(BaseModel):
    artifact_id: str
    run_id: str
    stage_run_id: str
    stage_name: str
    artifact_type: str
    storage_uri: str
    payload_format: str
    content_hash: str
    size_bytes: int
    record_count: int
    preview: dict[str, Any]
    created_at: str | None


class IndexStageRunResponse(BaseModel):
    stage_run_id: str
    run_id: str
    stage_name: str
    status: str
    sequence_no: int
    stale: bool
    summary: dict[str, Any]
    error_message: str | None
    started_at: str | None
    finished_at: str | None
    duration_ms: float | None
    artifact_count: int


class IndexPipelineRunResponse(BaseModel):
    run_id: str
    source_id: str
    status: str
    config: dict[str, Any]
    summary: dict[str, Any]
    error_message: str | None
    created_at: str | None
    started_at: str | None
    finished_at: str | None


class IndexPipelineRunDetailResponse(BaseModel):
    run: IndexPipelineRunResponse
    stages: list[IndexStageRunResponse]


class StageArtifactsResponseModel(BaseModel):
    stage_run: IndexStageRunResponse | None
    manifests: list[IndexArtifactManifestResponse]


class ArtifactDataResponse(BaseModel):
    manifest: IndexArtifactManifestResponse
    data: dict[str, Any] | list[dict[str, Any]]
    has_more: bool


@router.get("/parsers", response_model=list[SourceParserResponse])
async def source_parsers(
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> list[SourceParserResponse]:
    return [
        SourceParserResponse.model_validate(parser.to_dict())
        for parser in service.list_parsers()
    ]


@router.post("/preview", response_model=IndexingPreviewResponse)
async def preview_indexing(
    request: IndexingPreviewRequest,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexingPreviewResponse:
    try:
        result = await service.preview(
            PreviewIndexingCommand(
                parser=request.parser,
                parser_config=request.parser_config,
                chunker=request.chunker,
                chunk_config=request.chunk_config,
                source=SourceInput(
                    source_id=request.source.source_id,
                    notebook_id=request.source.notebook_id,
                    filename=request.source.filename,
                    media_type=request.source.media_type,
                    text=request.source.text,
                    file_path=request.source.file_path,
                    file_size=request.source.file_size,
                    input_blocks=tuple(
                        SourceInputBlock(
                            block_id=block.block_id,
                            block_type=block.block_type,
                            text=block.text,
                            page_no=block.page_no,
                            bbox=block.bbox,
                            section_hint=tuple(block.section_hint),
                            metadata=block.metadata,
                        )
                        for block in request.source.blocks
                    ),
                    metadata=request.source.metadata,
                ),
            )
        )
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (ConfigurationError, ExternalServiceError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return build_indexing_preview_response(result)


def build_indexing_preview_response(result) -> IndexingPreviewResponse:
    return IndexingPreviewResponse(
        effective_parser=result.effective_parser,
        effective_chunker=result.effective_chunker,
        effective_config=result.effective_config,
        blocks=[
            ContentBlockResponse.model_validate(
                {
                    **asdict(block),
                    "block_type": block.block_type.value,
                    "section_hint": list(block.section_hint),
                }
            )
            for block in result.document.blocks
        ],
        nodes=[
            IndexNodeResponse.model_validate(
                {
                    **asdict(node),
                    "section_path": list(node.section_path),
                    "block_ids": list(node.block_ids),
                }
            )
            for node in result.nodes
        ],
        summary=IndexingSummaryResponse.model_validate(asdict(result.summary)),
    )


@router.get("/jobs/{job_id}", response_model=IndexJobResponse)
async def get_indexing_job(
    job_id: str,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexJobResponse:
    try:
        job = await service.get_index_job(job_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return IndexJobResponse(
        job_id=job.job_id,
        source_id=job.source_id,
        status=job.status.value,
        requested_chunker=job.requested_chunker,
        effective_chunker=job.effective_chunker,
        config=job.config,
        summary=job.summary,
        error_message=job.error_message,
        vector_status=job.vector_status,
        vector_error_message=job.vector_error_message,
        node_count=job.node_count,
        requested_parser=job.requested_parser,
        effective_parser=job.effective_parser,
    )


@router.get("/jobs/{job_id}/artifacts", response_model=IndexingArtifactsResponse)
async def get_indexing_artifacts(
    job_id: str,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexingArtifactsResponse:
    try:
        result = await service.get_indexing_artifacts(job_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    vectorized_node_ids = [
        node.node_id
        for node in result.nodes
        if node.metadata.get("vector_point_id") is not None
    ]
    return IndexingArtifactsResponse(
        job=IndexJobResponse(
            job_id=result.job.job_id,
            source_id=result.job.source_id,
            status=result.job.status.value,
            requested_chunker=result.job.requested_chunker,
            effective_chunker=result.job.effective_chunker,
            config=result.job.config,
            summary=result.job.summary,
            error_message=result.job.error_message,
            vector_status=result.job.vector_status,
            vector_error_message=result.job.vector_error_message,
            node_count=result.job.node_count,
            requested_parser=result.job.requested_parser,
            effective_parser=result.job.effective_parser,
        ),
        blocks=[
            IndexBlockResponse.model_validate(
                {
                    **asdict(block),
                    "block_type": block.block_type.value,
                    "section_hint": list(block.section_hint),
                }
            )
            for block in result.blocks
        ],
        nodes=[
            IndexNodeResponse.model_validate(
                {
                    **asdict(node),
                    "section_path": list(node.section_path),
                    "block_ids": list(node.block_ids),
                }
            )
            for node in result.nodes
        ],
        vectorized_node_ids=vectorized_node_ids,
        metrics=result.job.summary,
    )


@router.get("/runs/latest", response_model=list[IndexPipelineRunResponse])
async def get_latest_indexing_pipeline_runs(
    service: Annotated[IndexingService, Depends(get_indexing_service)],
    limit: int = 100,
) -> list[IndexPipelineRunResponse]:
    try:
        runs = await service.list_latest_pipeline_runs(limit=limit)
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [build_pipeline_run_response(run) for run in runs]


@router.post("/runs/{run_id}/execute", response_model=IndexPipelineRunDetailResponse)
async def execute_indexing_pipeline_run(
    run_id: str,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexPipelineRunDetailResponse:
    try:
        result = await service.execute_pipeline_run(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (ConfigurationError, ExternalServiceError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return build_pipeline_run_detail_response(result)


@router.get("/runs/{run_id}", response_model=IndexPipelineRunDetailResponse)
async def get_indexing_pipeline_run(
    run_id: str,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexPipelineRunDetailResponse:
    try:
        result = await service.get_pipeline_run(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return build_pipeline_run_detail_response(result)


@router.post(
    "/runs/{run_id}/stages/{stage_name}/execute",
    response_model=StageArtifactsResponseModel,
)
async def execute_indexing_pipeline_stage(
    run_id: str,
    stage_name: str,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> StageArtifactsResponseModel:
    try:
        result = await service.execute_pipeline_stage(run_id, stage_name)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (ConfigurationError, ExternalServiceError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return build_stage_artifacts_response(result)


@router.get(
    "/runs/{run_id}/stages/{stage_name}/artifacts",
    response_model=StageArtifactsResponseModel,
)
async def get_indexing_stage_artifacts(
    run_id: str,
    stage_name: str,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> StageArtifactsResponseModel:
    try:
        result = await service.get_stage_artifacts(run_id, stage_name)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_stage_artifacts_response(result)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactDataResponse)
async def get_indexing_artifact_data(
    artifact_id: str,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
    offset: int = 0,
    limit: int = 50,
) -> ArtifactDataResponse:
    try:
        result = await service.get_artifact_data(
            artifact_id,
            offset=offset,
            limit=limit,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return build_artifact_data_response(result)


def build_pipeline_run_detail_response(
    result: IndexPipelineRunResult,
) -> IndexPipelineRunDetailResponse:
    return IndexPipelineRunDetailResponse(
        run=build_pipeline_run_response(result.run),
        stages=[build_stage_run_response(stage) for stage in result.stages],
    )


def build_stage_artifacts_response(
    result: StageArtifactsResult,
) -> StageArtifactsResponseModel:
    return StageArtifactsResponseModel(
        stage_run=build_stage_run_response(result.stage_run) if result.stage_run else None,
        manifests=[build_artifact_manifest_response(manifest) for manifest in result.manifests],
    )


def build_artifact_data_response(result: IndexArtifactDataResult) -> ArtifactDataResponse:
    return ArtifactDataResponse(
        manifest=build_artifact_manifest_response(result.manifest),
        data=result.data,
        has_more=result.has_more,
    )


def build_pipeline_run_response(run) -> IndexPipelineRunResponse:
    return IndexPipelineRunResponse(
        run_id=run.run_id,
        source_id=run.source_id,
        status=run.status.value,
        config=run.config,
        summary=run.summary,
        error_message=run.error_message,
        created_at=run.created_at.isoformat() if run.created_at else None,
        started_at=run.started_at.isoformat() if run.started_at else None,
        finished_at=run.finished_at.isoformat() if run.finished_at else None,
    )


def build_stage_run_response(stage) -> IndexStageRunResponse:
    return IndexStageRunResponse(
        stage_run_id=stage.stage_run_id,
        run_id=stage.run_id,
        stage_name=stage.stage_name.value,
        status=stage.status.value,
        sequence_no=stage.sequence_no,
        stale=stage.stale,
        summary=stage.summary,
        error_message=stage.error_message,
        started_at=stage.started_at.isoformat() if stage.started_at else None,
        finished_at=stage.finished_at.isoformat() if stage.finished_at else None,
        duration_ms=stage.duration_ms,
        artifact_count=stage.artifact_count,
    )


def build_artifact_manifest_response(manifest) -> IndexArtifactManifestResponse:
    return IndexArtifactManifestResponse(
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
        created_at=manifest.created_at.isoformat() if manifest.created_at else None,
    )
