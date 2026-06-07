from dataclasses import dataclass, field
from typing import Any

from ragmax.domain.indexing.entities import IndexNode


@dataclass(frozen=True)
class RetrievalCommand:
    query: str
    notebook_id: str
    top_k: int = 8
    source_ids: tuple[str, ...] = field(default_factory=tuple)
    content_types: tuple[str, ...] = field(default_factory=tuple)
    score_threshold: float | None = None


@dataclass(frozen=True)
class RetrievalCitation:
    source_id: str
    node_id: str
    filename: str | None
    page_label: str | None
    section_path: tuple[str, ...]


@dataclass(frozen=True)
class RetrievedNode:
    node: IndexNode
    score: float
    collection_name: str
    citation: RetrievalCitation
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    notebook_id: str
    results: tuple[RetrievedNode, ...]


@dataclass(frozen=True)
class RerankedNode:
    retrieved_node: RetrievedNode
    rank: int
    rerank_score: float
    vector_score: float
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalContextItem:
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
    section_path: tuple[str, ...]
    citation: RetrievalCitation
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnswerCommand:
    query: str
    notebook_id: str
    retrieval_top_k: int | None = None
    rerank_top_k: int | None = None
    source_ids: tuple[str, ...] = field(default_factory=tuple)
    content_types: tuple[str, ...] = field(default_factory=tuple)
    score_threshold: float | None = None


@dataclass(frozen=True)
class AnswerCitation:
    citation_id: str
    context_id: str
    citation: RetrievalCitation


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str
    used_context_ids: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AnswerResult:
    query: str
    notebook_id: str
    answer: str
    contexts: tuple[RetrievalContextItem, ...]
    citations: tuple[AnswerCitation, ...]
    retrieval_count: int
    rerank_count: int
    reranker_name: str
    answer_generator_name: str
    metadata: dict[str, Any] = field(default_factory=dict)
