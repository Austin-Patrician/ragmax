from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from ragmax.application.retrieval.dtos import (
    GeneratedAnswer,
    RerankedNode,
    RetrievalContextItem,
    RetrievedNode,
)


@dataclass(frozen=True)
class VectorSearchHit:
    node_id: str
    score: float
    collection_name: str
    payload: dict[str, Any] = field(default_factory=dict)


class VectorSearcher(Protocol):
    async def search(
        self,
        *,
        collection_names: Sequence[str],
        query_vector: Sequence[float],
        source_ids: Sequence[str],
        content_types: Sequence[str],
        limit: int,
        score_threshold: float | None = None,
    ) -> tuple[VectorSearchHit, ...]:
        ...


class Reranker(Protocol):
    name: str

    async def rerank(
        self,
        *,
        query: str,
        nodes: Sequence[RetrievedNode],
        top_k: int,
    ) -> tuple[RerankedNode, ...]:
        ...


class AnswerGenerator(Protocol):
    name: str

    async def generate(
        self,
        *,
        query: str,
        contexts: Sequence[RetrievalContextItem],
    ) -> GeneratedAnswer:
        ...
