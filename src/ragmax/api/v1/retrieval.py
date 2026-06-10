from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ragmax.api.auth_dependencies import ROUTE_RETRIEVAL, require_route_permission
from ragmax.api.dependencies import get_dataset_service, get_retrieval_service
from ragmax.application.datasets.service import DatasetService
from ragmax.application.retrieval.dtos import AnswerCommand, RetrievalCommand
from ragmax.application.retrieval.service import RetrievalService
from ragmax.core.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InvalidRequestError,
    NotFoundError,
)

router = APIRouter(
    prefix="/retrieval",
    tags=["retrieval"],
    dependencies=[Depends(require_route_permission(ROUTE_RETRIEVAL))],
)
logger = logging.getLogger(__name__)


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    top_k: int = Field(default=8, ge=1, le=100)
    content_types: list[str] = Field(default_factory=list)
    score_threshold: float | None = None


class RetrievalAnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    retrieval_top_k: int | None = Field(default=None, ge=1, le=100)
    rerank_top_k: int | None = Field(default=None, ge=1, le=100)
    content_types: list[str] = Field(default_factory=list)
    score_threshold: float | None = None


class RetrievalCitationResponse(BaseModel):
    source_id: str
    node_id: str
    filename: str | None
    page_label: str | None
    section_path: list[str]


class RetrievedNodeResponse(BaseModel):
    node_id: str
    source_id: str
    notebook_id: str
    text: str
    score: float
    collection_name: str
    content_type: str
    page_start: int | None
    page_end: int | None
    section_path: list[str]
    citation: RetrievalCitationResponse
    metadata: dict[str, Any]


class RetrievalSearchResponse(BaseModel):
    query: str
    dataset_id: str
    count: int
    results: list[RetrievedNodeResponse]


class RetrievalContextResponse(BaseModel):
    context_id: str
    citation_id: str
    node_id: str
    source_id: str
    notebook_id: str
    text: str
    score: float
    vector_score: float
    rerank_score: float
    collection_name: str
    content_type: str
    page_start: int | None
    page_end: int | None
    section_path: list[str]
    citation: RetrievalCitationResponse
    metadata: dict[str, Any]


class AnswerCitationResponse(BaseModel):
    citation_id: str
    context_id: str
    source_id: str
    node_id: str
    filename: str | None
    page_label: str | None
    section_path: list[str]


class RetrievalAnswerResponse(BaseModel):
    query: str
    dataset_id: str
    answer: str
    retrieval_count: int
    rerank_count: int
    reranker: str
    answer_generator: str
    contexts: list[RetrievalContextResponse]
    citations: list[AnswerCitationResponse]
    metadata: dict[str, Any]


@router.post("/search", response_model=RetrievalSearchResponse)
async def search_retrieval(
    request: RetrievalSearchRequest,
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
    dataset_service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> RetrievalSearchResponse:
    try:
        source_ids = await _source_ids_for_dataset(dataset_service, request.dataset_id)
        result = await service.search(
            RetrievalCommand(
                query=request.query,
                dataset_id=request.dataset_id,
                top_k=request.top_k,
                source_ids=source_ids,
                content_types=tuple(request.content_types),
                score_threshold=request.score_threshold,
            )
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (ConfigurationError, ExternalServiceError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RetrievalSearchResponse(
        query=result.query,
        dataset_id=result.dataset_id,
        count=len(result.results),
        results=[
            RetrievedNodeResponse(
                node_id=item.node.node_id,
                source_id=item.node.source_id,
                notebook_id=item.node.notebook_id,
                text=item.node.text,
                score=item.score,
                collection_name=item.collection_name,
                content_type=item.node.content_type,
                page_start=item.node.page_start,
                page_end=item.node.page_end,
                section_path=list(item.node.section_path),
                citation=RetrievalCitationResponse(
                    source_id=item.citation.source_id,
                    node_id=item.citation.node_id,
                    filename=item.citation.filename,
                    page_label=item.citation.page_label,
                    section_path=list(item.citation.section_path),
                ),
                metadata=item.node.metadata,
            )
            for item in result.results
        ],
    )


@router.post("/answer", response_class=StreamingResponse)
async def answer_retrieval(
    request: RetrievalAnswerRequest,
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
    dataset_service: Annotated[DatasetService, Depends(get_dataset_service)],
) -> StreamingResponse:
    request_id = uuid4().hex[:12]
    request_started_at = perf_counter()
    try:
        logger.info(
            "retrieval answer request started request_id=%s dataset_id=%s "
            "query_chars=%d retrieval_top_k=%s rerank_top_k=%s content_types=%d",
            request_id,
            request.dataset_id,
            len(request.query),
            request.retrieval_top_k,
            request.rerank_top_k,
            len(request.content_types),
        )

        source_ids_started_at = perf_counter()
        source_ids = await _source_ids_for_dataset(dataset_service, request.dataset_id)
        logger.info(
            "retrieval answer source ids loaded request_id=%s dataset_id=%s "
            "source_count=%d duration_ms=%.2f",
            request_id,
            request.dataset_id,
            len(source_ids),
            _elapsed_ms(source_ids_started_at),
        )

    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (ConfigurationError, ExternalServiceError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    command = AnswerCommand(
        query=request.query,
        dataset_id=request.dataset_id,
        retrieval_top_k=request.retrieval_top_k,
        rerank_top_k=request.rerank_top_k,
        source_ids=source_ids,
        content_types=tuple(request.content_types),
        score_threshold=request.score_threshold,
    )
    return StreamingResponse(
        _answer_event_stream(
            service=service,
            command=command,
            request_id=request_id,
            dataset_id=request.dataset_id,
            request_started_at=request_started_at,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _answer_event_stream(
    *,
    service: RetrievalService,
    command: AnswerCommand,
    request_id: str,
    dataset_id: str,
    request_started_at: float,
) -> AsyncIterator[str]:
    try:
        yield _sse_event(
            "status",
            {
                "stage": "accepted",
                "request_id": request_id,
                "dataset_id": dataset_id,
            },
        )
        async for event in service.answer_stream(command):
            yield _sse_event(event.event, _jsonable_stream_data(event.data))
            if event.event == "done":
                logger.info(
                    "retrieval answer stream completed request_id=%s dataset_id=%s "
                    "total_duration_ms=%.2f",
                    request_id,
                    dataset_id,
                    _elapsed_ms(request_started_at),
                )
    except (NotFoundError, InvalidRequestError, ConfigurationError, ExternalServiceError) as exc:
        logger.exception(
            "retrieval answer stream failed request_id=%s dataset_id=%s",
            request_id,
            dataset_id,
        )
        yield _sse_event(
            "error",
            {
                "request_id": request_id,
                "dataset_id": dataset_id,
                "message": str(exc),
                "error_type": exc.__class__.__name__,
            },
        )


async def _source_ids_for_dataset(
    dataset_service: DatasetService,
    dataset_id: str,
) -> tuple[str, ...]:
    files = await dataset_service.list_dataset_files(dataset_id)
    source_ids = tuple(file.source_id for file in files)
    if not source_ids:
        raise InvalidRequestError(f"Dataset '{dataset_id}' has no files.")
    return source_ids


def _sse_event(event: str, data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"


def _jsonable_stream_data(data: dict[str, Any]) -> dict[str, Any]:
    jsonable = dict(data)
    if "contexts" in jsonable:
        jsonable["contexts"] = [
            _context_response(context).model_dump(mode="json")
            for context in jsonable["contexts"]
        ]
    if "citations" in jsonable:
        jsonable["citations"] = [
            _answer_citation_response(citation).model_dump(mode="json")
            for citation in jsonable["citations"]
        ]
    return jsonable


def _context_response(context: Any) -> RetrievalContextResponse:
    return RetrievalContextResponse(
        context_id=context.context_id,
        citation_id=context.citation_id,
        node_id=context.node_id,
        source_id=context.source_id,
        notebook_id=context.notebook_id,
        text=context.text,
        score=context.score,
        vector_score=context.vector_score,
        rerank_score=context.rerank_score,
        collection_name=context.collection_name,
        content_type=context.content_type,
        page_start=context.page_start,
        page_end=context.page_end,
        section_path=list(context.section_path),
        citation=RetrievalCitationResponse(
            source_id=context.citation.source_id,
            node_id=context.citation.node_id,
            filename=context.citation.filename,
            page_label=context.citation.page_label,
            section_path=list(context.citation.section_path),
        ),
        metadata=context.metadata,
    )


def _answer_citation_response(citation: Any) -> AnswerCitationResponse:
    return AnswerCitationResponse(
        citation_id=citation.citation_id,
        context_id=citation.context_id,
        source_id=citation.citation.source_id,
        node_id=citation.citation.node_id,
        filename=citation.citation.filename,
        page_label=citation.citation.page_label,
        section_path=list(citation.citation.section_path),
    )


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000
