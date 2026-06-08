from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator

from ragmax.api.dependencies import get_indexing_service
from ragmax.application.indexing.dtos import (
    PreviewIndexingCommand,
    ProfileOverrides,
    SourceInput,
    SourceInputBlock,
)
from ragmax.application.indexing.service import IndexingService
from ragmax.core.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidRequestError,
    NotFoundError,
)

router = APIRouter(prefix="/indexing", tags=["indexing"])


class IndexingProfileResponse(BaseModel):
    name: str
    description: str
    chunker: str
    chunk_size: int = Field(gt=0)
    chunk_overlap: int = Field(ge=0)
    node_graph_mode: str
    supported_media_types: list[str]
    text_collection: str
    visual_collection: str
    options: dict[str, Any]


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


class ProfileOverridesPayload(BaseModel):
    chunk_size: int | None = Field(default=None, gt=0)
    chunk_overlap: int | None = Field(default=None, ge=0)
    options: dict[str, Any] = Field(default_factory=dict)


class IndexingPreviewRequest(BaseModel):
    profile_name: str | None = None
    parser_name: str | None = None
    parser_options: dict[str, Any] = Field(default_factory=dict)
    overrides: ProfileOverridesPayload = Field(default_factory=ProfileOverridesPayload)
    source: SourcePayload


class SourceAnalysisResponse(BaseModel):
    recommended_profile: str
    reasons: list[str]
    traits: dict[str, Any]


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
    requested_profile: str | None
    effective_profile: str | None
    requested_parser: str | None
    effective_parser: str | None
    overrides: dict[str, Any]
    summary: dict[str, Any]
    error_message: str | None
    vector_status: str | None
    vector_error_message: str | None
    node_count: int


class IndexingPreviewResponse(BaseModel):
    analysis: SourceAnalysisResponse
    effective_profile: IndexingProfileResponse
    effective_parser: str
    blocks: list[ContentBlockResponse]
    nodes: list[IndexNodeResponse]
    summary: IndexingSummaryResponse


class IndexingArtifactsResponse(BaseModel):
    job: IndexJobResponse
    blocks: list[IndexBlockResponse]
    nodes: list[IndexNodeResponse]
    vectorized_node_ids: list[str]
    metrics: dict[str, Any]


@router.get("/profiles", response_model=list[IndexingProfileResponse])
async def indexing_profiles(
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> list[IndexingProfileResponse]:
    return [
        IndexingProfileResponse.model_validate(profile.to_dict())
        for profile in service.list_profiles()
    ]


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
                profile_name=request.profile_name,
                parser_name=request.parser_name,
                parser_options=request.parser_options,
                overrides=ProfileOverrides(
                    chunk_size=request.overrides.chunk_size,
                    chunk_overlap=request.overrides.chunk_overlap,
                    options=request.overrides.options,
                ),
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
        analysis=SourceAnalysisResponse(
            recommended_profile=result.analysis.recommended_profile.value,
            reasons=list(result.analysis.reasons),
            traits=result.analysis.traits,
        ),
        effective_profile=IndexingProfileResponse.model_validate(result.effective_profile.to_dict()),
        effective_parser=result.effective_parser,
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
        requested_profile=job.requested_profile,
        effective_profile=job.effective_profile,
        overrides=job.overrides,
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
            requested_profile=result.job.requested_profile,
            effective_profile=result.job.effective_profile,
            overrides=result.job.overrides,
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
