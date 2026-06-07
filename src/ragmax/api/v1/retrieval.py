from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ragmax.api.dependencies import get_retrieval_service
from ragmax.application.retrieval.dtos import AnswerCommand, RetrievalCommand
from ragmax.application.retrieval.service import RetrievalService
from ragmax.core.exceptions import ConfigurationError, InvalidRequestError

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class RetrievalSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    notebook_id: str = Field(min_length=1)
    top_k: int = Field(default=8, ge=1, le=50)
    source_ids: list[str] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)
    score_threshold: float | None = None


class RetrievalAnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    notebook_id: str = Field(min_length=1)
    retrieval_top_k: int | None = Field(default=None, ge=1, le=50)
    rerank_top_k: int | None = Field(default=None, ge=1, le=50)
    source_ids: list[str] = Field(default_factory=list)
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
    notebook_id: str
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
    notebook_id: str
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
) -> RetrievalSearchResponse:
    try:
        result = await service.search(
            RetrievalCommand(
                query=request.query,
                notebook_id=request.notebook_id,
                top_k=request.top_k,
                source_ids=tuple(request.source_ids),
                content_types=tuple(request.content_types),
                score_threshold=request.score_threshold,
            )
        )
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RetrievalSearchResponse(
        query=result.query,
        notebook_id=result.notebook_id,
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


@router.post("/answer", response_model=RetrievalAnswerResponse)
async def answer_retrieval(
    request: RetrievalAnswerRequest,
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> RetrievalAnswerResponse:
    try:
        result = await service.answer(
            AnswerCommand(
                query=request.query,
                notebook_id=request.notebook_id,
                retrieval_top_k=request.retrieval_top_k,
                rerank_top_k=request.rerank_top_k,
                source_ids=tuple(request.source_ids),
                content_types=tuple(request.content_types),
                score_threshold=request.score_threshold,
            )
        )
    except InvalidRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RetrievalAnswerResponse(
        query=result.query,
        notebook_id=result.notebook_id,
        answer=result.answer,
        retrieval_count=result.retrieval_count,
        rerank_count=result.rerank_count,
        reranker=result.reranker_name,
        answer_generator=result.answer_generator_name,
        contexts=[
            RetrievalContextResponse(
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
            for context in result.contexts
        ],
        citations=[
            AnswerCitationResponse(
                citation_id=citation.citation_id,
                context_id=citation.context_id,
                source_id=citation.citation.source_id,
                node_id=citation.citation.node_id,
                filename=citation.citation.filename,
                page_label=citation.citation.page_label,
                section_path=list(citation.citation.section_path),
            )
            for citation in result.citations
        ],
        metadata=result.metadata,
    )
