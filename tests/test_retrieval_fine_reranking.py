from collections.abc import Sequence

import pytest

from ragmax.application.indexing.profiles import list_indexing_profiles
from ragmax.application.indexing.registry import IndexingProfileRegistry
from ragmax.application.retrieval.dtos import (
    AnswerCommand,
    GeneratedAnswer,
    RerankedNode,
    RetrievalCommand,
    RetrievalContextItem,
    RetrievedNode,
)
from ragmax.application.retrieval.fusion_dtos import BM25SearchHit
from ragmax.application.retrieval.ports import VectorSearchHit
from ragmax.application.retrieval.service import RetrievalService
from ragmax.domain.indexing.entities import IndexNode
from ragmax.infrastructure.indexing.embeddings.hash_embedding_provider import HashEmbeddingProvider
from ragmax.infrastructure.retrieval.fusion.rrf_fuser import RRFFuser


class FakeVectorSearcher:
    def __init__(self, hits: tuple[VectorSearchHit, ...]) -> None:
        self.hits = hits

    async def search(
        self,
        *,
        collection_names: Sequence[str],
        query_vector: Sequence[float],
        notebook_id: str,
        source_ids: Sequence[str],
        content_types: Sequence[str],
        limit: int,
        score_threshold: float | None = None,
    ) -> tuple[VectorSearchHit, ...]:
        del collection_names, query_vector, notebook_id, source_ids, content_types
        del score_threshold
        return self.hits[:limit]


class FakeBM25Searcher:
    def __init__(self, hits: tuple[BM25SearchHit, ...]) -> None:
        self.hits = hits
        self.calls: list[int] = []

    async def search(
        self,
        *,
        query: str,
        collection_names: Sequence[str],
        notebook_id: str,
        source_ids: Sequence[str],
        content_types: Sequence[str],
        limit: int,
    ) -> tuple[BM25SearchHit, ...]:
        del query, collection_names, notebook_id, source_ids, content_types
        self.calls.append(limit)
        return self.hits[:limit]


class OrderedReranker:
    def __init__(self, *, name: str, order: tuple[str, ...]) -> None:
        self.name = name
        self.order = order
        self.calls: list[tuple[tuple[str, ...], int]] = []

    async def rerank(
        self,
        *,
        query: str,
        nodes: Sequence[RetrievedNode],
        top_k: int,
    ) -> tuple[RerankedNode, ...]:
        del query
        self.calls.append((tuple(node.node.node_id for node in nodes), top_k))
        rank_by_id = {node_id: index for index, node_id in enumerate(self.order)}
        ordered = sorted(
            nodes,
            key=lambda node: rank_by_id.get(node.node.node_id, len(rank_by_id)),
        )[:top_k]
        return tuple(
            RerankedNode(
                retrieved_node=node,
                rank=rank,
                rerank_score=1.0 / rank,
                vector_score=node.score,
                reason=self.name,
                metadata={"stage": self.name},
            )
            for rank, node in enumerate(ordered, start=1)
        )


class FakeAnswerGenerator:
    name = "fake_answer_generator"

    async def generate(
        self,
        *,
        query: str,
        contexts: Sequence[RetrievalContextItem],
    ) -> GeneratedAnswer:
        del query
        return GeneratedAnswer(
            answer="answer",
            used_context_ids=tuple(context.context_id for context in contexts),
            metadata={},
        )


class FakeNodeRepository:
    def __init__(self, nodes: dict[str, IndexNode]) -> None:
        self._nodes = nodes

    async def get_many(self, node_ids: Sequence[str]) -> tuple[IndexNode, ...]:
        return tuple(self._nodes[node_id] for node_id in node_ids if node_id in self._nodes)


class FakeUnitOfWork:
    def __init__(self, nodes: dict[str, IndexNode]) -> None:
        self.nodes = FakeNodeRepository(nodes)

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb


@pytest.mark.asyncio
async def test_answer_uses_coarse_then_fine_reranking_pipeline() -> None:
    nodes = {
        "node-1": _node("node-1", "refund approval policy"),
        "node-2": _node("node-2", "inventory update"),
    }
    coarse = OrderedReranker(name="coarse_reranker", order=("node-2", "node-1"))
    fine = OrderedReranker(name="fine_reranker", order=("node-1", "node-2"))
    service = RetrievalService(
        embedding_provider=HashEmbeddingProvider(model_name="hash-test", dimension=8),
        vector_searcher=FakeVectorSearcher(
            (
                VectorSearchHit(
                    node_id="node-1",
                    score=0.8,
                    collection_name="ragmax_text_nodes",
                    payload={"node_id": "node-1"},
                ),
                VectorSearchHit(
                    node_id="node-2",
                    score=0.9,
                    collection_name="ragmax_text_nodes",
                    payload={"node_id": "node-2"},
                ),
            )
        ),
        reranker=coarse,
        fine_reranker=fine,
        answer_generator=FakeAnswerGenerator(),
        profile_registry=IndexingProfileRegistry(list_indexing_profiles()),
        unit_of_work_factory=lambda: FakeUnitOfWork(nodes),
        default_top_k=2,
        max_top_k=100,
        default_rerank_top_k=2,
        bm25_top_k=10,
        reranking_stages=("coarse", "fine"),
        coarse_top_k=2,
        fine_top_k=1,
        max_context_items=2,
    )

    result = await service.answer(AnswerCommand(query="approval", notebook_id="notebook-1"))

    assert coarse.calls == [(("node-2", "node-1"), 2)]
    assert fine.calls == [(("node-2", "node-1"), 1)]
    assert result.reranker_name == "coarse_reranker+fine_reranker"
    assert [context.node_id for context in result.contexts] == ["node-1"]
    assert result.metadata["reranking"]["stages"] == ["coarse", "fine"]


@pytest.mark.asyncio
async def test_search_uses_configured_bm25_candidate_limit() -> None:
    nodes = {
        "node-1": _node("node-1", "refund approval policy"),
        "node-2": _node("node-2", "inventory update"),
    }
    bm25_searcher = FakeBM25Searcher(
        (
            BM25SearchHit(
                node_id="node-1",
                score=3.0,
                collection_name="ragmax_text_nodes",
                matched_terms=("refund",),
                payload={"node_id": "node-1"},
            ),
        )
    )
    service = RetrievalService(
        embedding_provider=HashEmbeddingProvider(model_name="hash-test", dimension=8),
        vector_searcher=FakeVectorSearcher(
            (
                VectorSearchHit(
                    node_id="node-2",
                    score=0.9,
                    collection_name="ragmax_text_nodes",
                    payload={"node_id": "node-2"},
                ),
            )
        ),
        reranker=OrderedReranker(name="coarse_reranker", order=("node-1", "node-2")),
        fine_reranker=None,
        answer_generator=FakeAnswerGenerator(),
        profile_registry=IndexingProfileRegistry(list_indexing_profiles()),
        unit_of_work_factory=lambda: FakeUnitOfWork(nodes),
        default_top_k=2,
        max_top_k=100,
        default_rerank_top_k=2,
        bm25_top_k=7,
        reranking_stages=("coarse",),
        coarse_top_k=2,
        fine_top_k=1,
        max_context_items=2,
        bm25_searcher=bm25_searcher,
        search_fuser=RRFFuser(),
    )

    result = await service.search(
        RetrievalCommand(query="refund", notebook_id="notebook-1", top_k=2)
    )

    assert bm25_searcher.calls == [7]
    assert {item.node.node_id for item in result.results} == {"node-1", "node-2"}
    bm25_only = next(item for item in result.results if item.node.node_id == "node-1")
    assert bm25_only.collection_name == "ragmax_text_nodes"
    assert bm25_only.payload["bm25_matched_terms"] == ("refund",)


def _node(node_id: str, text: str) -> IndexNode:
    return IndexNode(
        node_id=node_id,
        source_id="source-1",
        notebook_id="notebook-1",
        text=text,
        modality="text",
        content_type="paragraph",
        metadata={"source_filename": "guide.md"},
    )
