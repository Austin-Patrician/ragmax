from __future__ import annotations

import json
import mimetypes
from dataclasses import asdict
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field, model_validator

from ragmax.api.dependencies import get_indexing_service, get_source_storage
from ragmax.api.v1.indexing import (
    IndexingPreviewResponse,
    IndexingProfileResponse,
    IndexingSummaryResponse,
    ProfileOverridesPayload,
    build_indexing_preview_response,
)
from ragmax.application.indexing.dtos import (
    CreateSourceCommand,
    PreviewIndexingCommand,
    ProfileOverrides,
    RunIndexJobCommand,
    SourceInputBlock,
)
from ragmax.application.indexing.service import IndexingService
from ragmax.core.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidRequestError,
    NotFoundError,
)
from ragmax.domain.indexing.entities import IndexNode
from ragmax.domain.indexing.records import IndexJobRecord, SourceRecord
from ragmax.infrastructure.storage.local_source_storage import LocalSourceStorage

router = APIRouter(prefix="/sources", tags=["sources"])


class ContentBlockPayload(BaseModel):
    block_id: str | None = None
    block_type: str = "text"
    text: str = ""
    page_no: int | None = None
    bbox: tuple[float, float, float, float] | None = None
    section_hint: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateSourceRequest(BaseModel):
    source_id: str | None = None
    notebook_id: str
    filename: str
    media_type: str
    text: str | None = None
    blocks: list[ContentBlockPayload] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_content(self) -> CreateSourceRequest:
        has_text = bool(self.text and self.text.strip())
        has_blocks = bool(self.blocks)
        if not has_text and not has_blocks:
            raise ValueError("Provide source.text or source.blocks.")
        return self


class SourceResponse(BaseModel):
    source_id: str
    notebook_id: str
    filename: str
    media_type: str
    source_hash: str
    text: str | None
    input_blocks: list[dict[str, Any]]
    has_file: bool
    file_size: int | None
    metadata: dict[str, Any]


class RunIndexJobRequest(BaseModel):
    profile_name: str | None = None
    parser_name: str | None = None
    parser_options: dict[str, Any] = Field(default_factory=dict)
    overrides: ProfileOverridesPayload = Field(default_factory=ProfileOverridesPayload)


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


class RunIndexJobResponse(BaseModel):
    job: IndexJobResponse
    source: SourceResponse
    effective_profile: IndexingProfileResponse
    effective_parser: str
    summary: IndexingSummaryResponse
    node_count: int


class DeleteSourceIndexResponse(BaseModel):
    source_id: str
    deleted_count: int
    vector_deleted_count: int


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(
    request: CreateSourceRequest,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> SourceResponse:
    try:
        source = await service.create_source(
            CreateSourceCommand(
                source_id=request.source_id,
                notebook_id=request.notebook_id,
                filename=request.filename,
                media_type=request.media_type,
                text=request.text,
                input_blocks=tuple(_to_source_input_block(block) for block in request.blocks),
                metadata=request.metadata,
            )
        )
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _source_response(source)


@router.post("/upload", response_model=SourceResponse, status_code=201)
async def upload_source(
    service: Annotated[IndexingService, Depends(get_indexing_service)],
    storage: Annotated[LocalSourceStorage, Depends(get_source_storage)],
    file: Annotated[UploadFile, File()],
    notebook_id: Annotated[str, Form()],
    source_id: Annotated[str | None, Form()] = None,
    metadata: Annotated[str | None, Form()] = None,
) -> SourceResponse:
    generated_source_id = source_id or f"src_{uuid4().hex}"
    try:
        metadata_dict = _parse_metadata_form(metadata)
        stored_file = await storage.save_upload(
            source_id=generated_source_id,
            upload=file,
        )
        source = await service.create_source(
            CreateSourceCommand(
                source_id=generated_source_id,
                notebook_id=notebook_id,
                filename=stored_file.filename,
                media_type=_media_type_for_upload(file, stored_file.filename),
                source_hash=stored_file.sha256,
                file_path=str(stored_file.path),
                file_size=stored_file.size_bytes,
                metadata={
                    **metadata_dict,
                    "source_kind": "file",
                    "storage_key": stored_file.storage_key,
                },
            )
        )
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _source_response(source)


@router.post("/{source_id}/index/preview", response_model=IndexingPreviewResponse)
async def preview_source_indexing(
    source_id: str,
    request: RunIndexJobRequest,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexingPreviewResponse:
    try:
        source = await service.get_source_for_indexing(source_id)
        result = await service.preview(
            PreviewIndexingCommand(
                source=source,
                profile_name=request.profile_name,
                parser_name=request.parser_name,
                parser_options=request.parser_options,
                overrides=ProfileOverrides(
                    chunk_size=request.overrides.chunk_size,
                    chunk_overlap=request.overrides.chunk_overlap,
                    options=request.overrides.options,
                ),
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (ConfigurationError, ExternalServiceError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return build_indexing_preview_response(result)


@router.post("/{source_id}/index", response_model=RunIndexJobResponse)
async def run_source_indexing(
    source_id: str,
    request: RunIndexJobRequest,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> RunIndexJobResponse:
    try:
        result = await service.run_index_job(
            RunIndexJobCommand(
                source_id=source_id,
                profile_name=request.profile_name,
                parser_name=request.parser_name,
                parser_options=request.parser_options,
                overrides=ProfileOverrides(
                    chunk_size=request.overrides.chunk_size,
                    chunk_overlap=request.overrides.chunk_overlap,
                    options=request.overrides.options,
                ),
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (ConfigurationError, ExternalServiceError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RunIndexJobResponse(
        job=_job_response(result.job),
        source=_source_response(result.source),
        effective_profile=IndexingProfileResponse.model_validate(
            result.effective_profile.to_dict()
        ),
        effective_parser=result.effective_parser,
        summary=IndexingSummaryResponse.model_validate(asdict(result.summary)),
        node_count=len(result.nodes),
    )


@router.get("/{source_id}/nodes", response_model=list[IndexNodeResponse])
async def list_source_nodes(
    source_id: str,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> list[IndexNodeResponse]:
    try:
        nodes = await service.list_source_nodes(source_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [_node_response(node) for node in nodes]


@router.delete("/{source_id}/index", response_model=DeleteSourceIndexResponse)
async def delete_source_index(
    source_id: str,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> DeleteSourceIndexResponse:
    try:
        result = await service.delete_source_index(source_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DeleteSourceIndexResponse(
        source_id=result.source_id,
        deleted_count=result.deleted_count,
        vector_deleted_count=result.vector_deleted_count,
    )


def _to_source_input_block(block: ContentBlockPayload) -> SourceInputBlock:
    return SourceInputBlock(
        block_id=block.block_id,
        block_type=block.block_type,
        text=block.text,
        page_no=block.page_no,
        bbox=block.bbox,
        section_hint=tuple(block.section_hint),
        metadata=block.metadata,
    )


def _source_response(source: SourceRecord) -> SourceResponse:
    return SourceResponse(
        source_id=source.source_id,
        notebook_id=source.notebook_id,
        filename=source.filename,
        media_type=source.media_type,
        source_hash=source.source_hash,
        text=source.text,
        input_blocks=list(source.input_blocks),
        has_file=source.file_path is not None,
        file_size=source.file_size,
        metadata=source.metadata,
    )


def _job_response(job: IndexJobRecord) -> IndexJobResponse:
    return IndexJobResponse(
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
    )


def _parse_metadata_form(metadata: str | None) -> dict[str, Any]:
    if metadata is None or not metadata.strip():
        return {}
    try:
        value = json.loads(metadata)
    except json.JSONDecodeError as exc:
        raise InvalidRequestError("metadata must be a valid JSON object.") from exc
    if not isinstance(value, dict):
        raise InvalidRequestError("metadata must be a valid JSON object.")
    return dict(value)


def _media_type_for_upload(file: UploadFile, filename: str) -> str:
    if file.content_type and file.content_type not in {
        "application/octet-stream",
        "multipart/form-data",
    }:
        return file.content_type
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _node_response(node: IndexNode) -> IndexNodeResponse:
    return IndexNodeResponse.model_validate(
        {
            **asdict(node),
            "section_path": list(node.section_path),
            "block_ids": list(node.block_ids),
        }
    )
