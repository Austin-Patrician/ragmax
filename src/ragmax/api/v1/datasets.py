from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ragmax.api.auth_dependencies import ROUTE_INDEXING, require_route_permission
from ragmax.api.dependencies import get_dataset_service, get_indexing_service
from ragmax.application.datasets.dtos import (
    AddFilesToDatasetCommand,
    CreateDatasetCommand,
    DatasetWithFiles,
    RemoveFileFromDatasetCommand,
    UpdateDatasetCommand,
)
from ragmax.application.datasets.service import DatasetService
from ragmax.application.indexing.service import IndexingService
from ragmax.core.exceptions import InvalidRequestError, NotFoundError
from ragmax.domain.datasets.records import DatasetFileRecord, DatasetRecord

router = APIRouter(
    prefix="/datasets",
    tags=["datasets"],
    dependencies=[Depends(require_route_permission(ROUTE_INDEXING))],
)


class CreateDatasetRequest(BaseModel):
    name: str
    dataset_id: str | None = None
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateDatasetRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class AddFilesRequest(BaseModel):
    source_ids: list[str]


class DatasetResponse(BaseModel):
    dataset_id: str
    name: str
    description: str | None
    config: dict[str, Any]
    metadata: dict[str, Any]
    created_at: str | None
    updated_at: str | None


class DatasetFileResponse(BaseModel):
    id: int
    dataset_id: str
    source_id: str
    added_at: str | None


class DatasetWithFilesResponse(BaseModel):
    dataset: DatasetResponse
    files: list[DatasetFileResponse]
    file_count: int


@router.post("", response_model=DatasetResponse, status_code=201)
async def create_dataset(
    request: CreateDatasetRequest,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> DatasetResponse:
    try:
        dataset = await service.create_dataset(
            CreateDatasetCommand(
                name=request.name,
                dataset_id=request.dataset_id,
                description=request.description,
                config=request.config,
                metadata=request.metadata,
            )
        )
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _dataset_response(dataset)


@router.get("", response_model=list[DatasetResponse])
async def list_datasets(
    service: Annotated[DatasetService, Depends(get_dataset_service)],
    limit: int = 100,
    offset: int = 0,
) -> list[DatasetResponse]:
    datasets = await service.list_datasets(limit=limit, offset=offset)
    return [_dataset_response(dataset) for dataset in datasets]


@router.get("/{dataset_id}", response_model=DatasetWithFilesResponse)
async def get_dataset(
    dataset_id: str,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> DatasetWithFilesResponse:
    try:
        result = await service.get_dataset_with_files(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _dataset_with_files_response(result)


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str,
    request: UpdateDatasetRequest,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> DatasetResponse:
    try:
        dataset = await service.update_dataset(
            UpdateDatasetCommand(
                dataset_id=dataset_id,
                name=request.name,
                description=request.description,
                config=request.config,
                metadata=request.metadata,
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _dataset_response(dataset)


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: str,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> None:
    try:
        await service.delete_dataset(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{dataset_id}/files", response_model=list[DatasetFileResponse])
async def add_files_to_dataset(
    dataset_id: str,
    request: AddFilesRequest,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> list[DatasetFileResponse]:
    try:
        files = await service.add_files_to_dataset(
            AddFilesToDatasetCommand(
                dataset_id=dataset_id,
                source_ids=tuple(request.source_ids),
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [_dataset_file_response(file) for file in files]


@router.delete("/{dataset_id}/files/{source_id}", status_code=204)
async def remove_file_from_dataset(
    dataset_id: str,
    source_id: str,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> None:
    try:
        await service.remove_file_from_dataset(
            RemoveFileFromDatasetCommand(
                dataset_id=dataset_id,
                source_id=source_id,
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{dataset_id}/files", response_model=list[DatasetFileResponse])
async def list_dataset_files(
    dataset_id: str,
    service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> list[DatasetFileResponse]:
    try:
        files = await service.list_dataset_files(dataset_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return [_dataset_file_response(file) for file in files]


def _dataset_response(dataset: DatasetRecord) -> DatasetResponse:
    return DatasetResponse(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        description=dataset.description,
        config=dataset.config,
        metadata=dataset.metadata,
        created_at=dataset.created_at.isoformat() if dataset.created_at else None,
        updated_at=dataset.updated_at.isoformat() if dataset.updated_at else None,
    )


def _dataset_file_response(file: DatasetFileRecord) -> DatasetFileResponse:
    return DatasetFileResponse(
        id=file.id,
        dataset_id=file.dataset_id,
        source_id=file.source_id,
        added_at=file.added_at.isoformat() if file.added_at else None,
    )


def _dataset_with_files_response(result: DatasetWithFiles) -> DatasetWithFilesResponse:
    return DatasetWithFilesResponse(
        dataset=_dataset_response(result.dataset),
        files=[_dataset_file_response(file) for file in result.files],
        file_count=result.file_count,
    )
