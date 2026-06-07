from collections.abc import Callable

from ragmax.application.indexing.ports import EmbeddingProvider, IndexingUnitOfWork
from ragmax.application.indexing.registry import IndexingProfileRegistry
from ragmax.application.retrieval.dtos import (
    AnswerCitation,
    AnswerCommand,
    AnswerResult,
    RerankedNode,
    RetrievalCitation,
    RetrievalCommand,
    RetrievalContextItem,
    RetrievalResult,
    RetrievedNode,
)
from ragmax.application.retrieval.ports import AnswerGenerator, Reranker, VectorSearcher
from ragmax.core.exceptions import ConfigurationError, InvalidRequestError
from ragmax.domain.indexing.entities import IndexNode

IndexingUnitOfWorkFactory = Callable[[], IndexingUnitOfWork]


class RetrievalService:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None,
        vector_searcher: VectorSearcher | None,
        reranker: Reranker | None,
        answer_generator: AnswerGenerator | None,
        profile_registry: IndexingProfileRegistry,
        unit_of_work_factory: IndexingUnitOfWorkFactory,
        default_top_k: int,
        max_top_k: int,
        default_rerank_top_k: int,
        max_context_items: int,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_searcher = vector_searcher
        self._reranker = reranker
        self._answer_generator = answer_generator
        self._profile_registry = profile_registry
        self._unit_of_work_factory = unit_of_work_factory
        self._default_top_k = default_top_k
        self._max_top_k = max_top_k
        self._default_rerank_top_k = default_rerank_top_k
        self._max_context_items = max(1, max_context_items)

    async def search(self, command: RetrievalCommand) -> RetrievalResult:
        self._ensure_configured()
        query = _normalize_query(command.query)

        top_k = self._resolve_top_k(
            command.top_k,
            default_top_k=self._default_top_k,
            field_name="top_k",
        )

        query_vector = (await self._embedding_provider.embed_texts([query]))[0]
        hits = await self._vector_searcher.search(
            collection_names=self._text_collection_names(),
            query_vector=query_vector,
            notebook_id=command.notebook_id,
            source_ids=command.source_ids,
            content_types=command.content_types,
            limit=top_k,
            score_threshold=command.score_threshold,
        )
        hydrated_nodes = await self._hydrate_nodes(tuple(hit.node_id for hit in hits))
        nodes_by_id = {node.node_id: node for node in hydrated_nodes}

        results: list[RetrievedNode] = []
        seen_node_ids: set[str] = set()
        for hit in hits:
            if hit.node_id in seen_node_ids:
                continue
            node = nodes_by_id.get(hit.node_id)
            if node is None:
                continue

            seen_node_ids.add(hit.node_id)
            results.append(
                RetrievedNode(
                    node=node,
                    score=hit.score,
                    collection_name=hit.collection_name,
                    citation=_citation_from_node(node),
                    payload=hit.payload,
                )
            )
            if len(results) >= top_k:
                break

        return RetrievalResult(
            query=query,
            notebook_id=command.notebook_id,
            results=tuple(results),
        )

    async def answer(self, command: AnswerCommand) -> AnswerResult:
        self._ensure_configured()
        self._ensure_answer_configured()
        query = _normalize_query(command.query)

        retrieval_top_k = self._resolve_top_k(
            command.retrieval_top_k,
            default_top_k=self._default_top_k,
            field_name="retrieval_top_k",
        )
        rerank_top_k = self._resolve_top_k(
            command.rerank_top_k,
            default_top_k=self._default_rerank_top_k,
            field_name="rerank_top_k",
        )

        retrieval_result = await self.search(
            RetrievalCommand(
                query=query,
                notebook_id=command.notebook_id,
                top_k=retrieval_top_k,
                source_ids=command.source_ids,
                content_types=command.content_types,
                score_threshold=command.score_threshold,
            )
        )
        reranked_nodes = await self._reranker.rerank(
            query=query,
            nodes=retrieval_result.results,
            top_k=min(rerank_top_k, len(retrieval_result.results)),
        )
        contexts = _context_items_from_reranked(
            reranked_nodes[: self._max_context_items]
        )
        generated_answer = await self._answer_generator.generate(
            query=query,
            contexts=contexts,
        )
        citations = _answer_citations_from_contexts(
            contexts=contexts,
            used_context_ids=generated_answer.used_context_ids,
        )

        return AnswerResult(
            query=query,
            notebook_id=command.notebook_id,
            answer=generated_answer.answer,
            contexts=contexts,
            citations=citations,
            retrieval_count=len(retrieval_result.results),
            rerank_count=len(reranked_nodes),
            reranker_name=self._reranker.name,
            answer_generator_name=self._answer_generator.name,
            metadata=generated_answer.metadata,
        )

    async def _hydrate_nodes(self, node_ids: tuple[str, ...]) -> tuple[IndexNode, ...]:
        async with self._unit_of_work_factory() as uow:
            return await uow.nodes.get_many(node_ids)

    def _text_collection_names(self) -> tuple[str, ...]:
        return tuple(
            sorted({profile.text_collection for profile in self._profile_registry.list()})
        )

    def _ensure_configured(self) -> None:
        if self._embedding_provider is None or self._vector_searcher is None:
            raise ConfigurationError("Retrieval is not configured.")

    def _ensure_answer_configured(self) -> None:
        if self._reranker is None:
            raise ConfigurationError("Reranker is not configured.")
        if self._answer_generator is None:
            raise ConfigurationError("Answer generation is not configured.")

    def _resolve_top_k(
        self,
        value: int | None,
        *,
        default_top_k: int,
        field_name: str,
    ) -> int:
        top_k = value or default_top_k
        if top_k < 1 or top_k > self._max_top_k:
            raise InvalidRequestError(
                f"{field_name} must be between 1 and {self._max_top_k}."
            )
        return top_k


def _normalize_query(query: str) -> str:
    normalized_query = query.strip()
    if not normalized_query:
        raise InvalidRequestError("Retrieval query must not be empty.")
    return normalized_query


def _context_items_from_reranked(
    reranked_nodes: tuple[RerankedNode, ...],
) -> tuple[RetrievalContextItem, ...]:
    contexts: list[RetrievalContextItem] = []
    for index, reranked_node in enumerate(reranked_nodes, start=1):
        retrieved_node = reranked_node.retrieved_node
        node = retrieved_node.node
        metadata = dict(node.metadata)
        metadata["retrieval"] = {
            "rank": reranked_node.rank,
            "vector_score": reranked_node.vector_score,
            "rerank_score": reranked_node.rerank_score,
            "rerank_reason": reranked_node.reason,
            "rerank_metadata": reranked_node.metadata,
            "payload": retrieved_node.payload,
        }
        contexts.append(
            RetrievalContextItem(
                context_id=f"ctx_{index}",
                citation_id=str(index),
                node_id=node.node_id,
                source_id=node.source_id,
                notebook_id=node.notebook_id,
                text=node.text,
                score=reranked_node.rerank_score,
                vector_score=reranked_node.vector_score,
                rerank_score=reranked_node.rerank_score,
                collection_name=retrieved_node.collection_name,
                content_type=node.content_type,
                page_start=node.page_start,
                page_end=node.page_end,
                section_path=node.section_path,
                citation=retrieved_node.citation,
                metadata=metadata,
            )
        )
    return tuple(contexts)


def _answer_citations_from_contexts(
    *,
    contexts: tuple[RetrievalContextItem, ...],
    used_context_ids: tuple[str, ...],
) -> tuple[AnswerCitation, ...]:
    contexts_by_id = {context.context_id: context for context in contexts}
    citations: list[AnswerCitation] = []
    for context_id in used_context_ids:
        context = contexts_by_id.get(context_id)
        if context is None:
            continue
        citations.append(
            AnswerCitation(
                citation_id=context.citation_id,
                context_id=context.context_id,
                citation=context.citation,
            )
        )
    return tuple(citations)


def _citation_from_node(node: IndexNode) -> RetrievalCitation:
    filename = node.metadata.get("source_filename")
    return RetrievalCitation(
        source_id=node.source_id,
        node_id=node.node_id,
        filename=str(filename) if filename else None,
        page_label=_page_label(node.page_start, node.page_end),
        section_path=node.section_path,
    )


def _page_label(page_start: int | None, page_end: int | None) -> str | None:
    if page_start is None and page_end is None:
        return None
    if page_start == page_end or page_end is None:
        return str(page_start)
    if page_start is None:
        return str(page_end)
    return f"{page_start}-{page_end}"
