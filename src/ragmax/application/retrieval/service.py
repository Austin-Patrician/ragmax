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
from ragmax.application.retrieval.fusion_ports import BM25Searcher, SearchFuser
from ragmax.application.retrieval.ports import (
    AnswerGenerator,
    Reranker,
    VectorSearcher,
    VectorSearchHit,
)
from ragmax.application.retrieval.query_dtos import NormalizedQuery
from ragmax.application.retrieval.query_ports import QueryNormalizer, QueryTransformer
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
        fine_reranker: Reranker | None,
        answer_generator: AnswerGenerator | None,
        profile_registry: IndexingProfileRegistry,
        unit_of_work_factory: IndexingUnitOfWorkFactory,
        default_top_k: int,
        max_top_k: int,
        default_rerank_top_k: int,
        bm25_top_k: int,
        reranking_stages: tuple[str, ...],
        coarse_top_k: int,
        fine_top_k: int,
        max_context_items: int,
        query_normalizer: QueryNormalizer | None = None,
        query_transformer: QueryTransformer | None = None,
        bm25_searcher: BM25Searcher | None = None,
        search_fuser: SearchFuser | None = None,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._vector_searcher = vector_searcher
        self._reranker = reranker
        self._fine_reranker = fine_reranker
        self._answer_generator = answer_generator
        self._profile_registry = profile_registry
        self._unit_of_work_factory = unit_of_work_factory
        self._default_top_k = default_top_k
        self._max_top_k = max_top_k
        self._default_rerank_top_k = default_rerank_top_k
        self._bm25_top_k = self._normalize_configured_top_k(bm25_top_k, "bm25_top_k")
        self._reranking_stages = reranking_stages
        self._coarse_top_k = self._normalize_configured_top_k(coarse_top_k, "coarse_top_k")
        self._fine_top_k = self._normalize_configured_top_k(fine_top_k, "fine_top_k")
        self._max_context_items = max(1, max_context_items)
        self._query_normalizer = query_normalizer
        self._query_transformer = query_transformer
        self._bm25_searcher = bm25_searcher
        self._search_fuser = search_fuser

    async def search(self, command: RetrievalCommand) -> RetrievalResult:
        self._ensure_configured()

        # 1. Query normalization
        normalized_query = self._normalize_query_text(command.query)

        # 2. Query transformation (if enabled)
        transformed_query = await self._transform_query(normalized_query)

        top_k = self._resolve_top_k(
            command.top_k,
            default_top_k=self._default_top_k,
            field_name="top_k",
        )

        # 3. Hybrid search: Vector + BM25 (if enabled)
        if self._bm25_searcher and self._search_fuser:
            # Perform both vector and BM25 search concurrently
            import asyncio

            vector_hits, bm25_hits = await asyncio.gather(
                self._vector_search_with_variants(transformed_query, command, top_k),
                self._bm25_search_with_variants(
                    transformed_query,
                    command,
                    self._bm25_top_k,
                ),
            )

            # Fuse results using RRF
            fused_hits = self._search_fuser.fuse(
                vector_hits=vector_hits, bm25_hits=bm25_hits, top_k=top_k
            )

            # Convert fused hits to VectorSearchHit format for backward compatibility
            hits = tuple(
                VectorSearchHit(
                    node_id=hit.node_id,
                    score=hit.fused_score,
                    collection_name=hit.collection_name,
                    payload={
                        "retrieval_mode": "hybrid",
                        "fused_score": hit.fused_score,
                        "vector_score": hit.vector_score,
                        "bm25_score": hit.bm25_score,
                        "vector_rank": hit.vector_rank,
                        "bm25_rank": hit.bm25_rank,
                        "bm25_matched_terms": hit.matched_terms,
                        **hit.payload,
                    },
                )
                for hit in fused_hits
            )
        else:
            # Vector-only search (original behavior)
            hits = await self._vector_search_with_variants(
                transformed_query, command, top_k
            )

        hydrated_nodes = await self._hydrate_nodes(tuple(hit.node_id for hit in hits))
        nodes_by_id = {node.node_id: node for node in hydrated_nodes}
        context_nodes_by_child_id = await self._hydrate_parent_contexts(hydrated_nodes)

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
                    context_node=context_nodes_by_child_id.get(node.node_id),
                    payload=hit.payload,
                )
            )
            if len(results) >= top_k:
                break

        return RetrievalResult(
            query=normalized_query.normalized,
            notebook_id=command.notebook_id,
            results=tuple(results),
        )

    async def answer(self, command: AnswerCommand) -> AnswerResult:
        self._ensure_configured()
        self._ensure_answer_configured()

        # Query normalization
        normalized_query = self._normalize_query_text(command.query)
        query = normalized_query.normalized

        fine_enabled = self._fine_reranking_enabled()
        retrieval_default_top_k = self._coarse_top_k if fine_enabled else self._default_top_k
        rerank_default_top_k = self._fine_top_k if fine_enabled else self._default_rerank_top_k

        retrieval_top_k = self._resolve_top_k(
            command.retrieval_top_k,
            default_top_k=retrieval_default_top_k,
            field_name="retrieval_top_k",
        )
        rerank_top_k = self._resolve_top_k(
            command.rerank_top_k,
            default_top_k=rerank_default_top_k,
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

        reranked_nodes = await self._rerank_answer_nodes(
            query=query,
            nodes=retrieval_result.results,
            top_k=rerank_top_k,
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
            reranker_name=self._reranker_name(),
            answer_generator_name=self._answer_generator.name,
            metadata={
                **generated_answer.metadata,
                "reranking": {
                    "stages": list(self._reranking_stages),
                    "coarse_reranker": self._reranker.name,
                    "fine_reranker": self._fine_reranker.name
                    if self._fine_reranker is not None
                    else None,
                },
            },
        )

    async def _hydrate_nodes(self, node_ids: tuple[str, ...]) -> tuple[IndexNode, ...]:
        async with self._unit_of_work_factory() as uow:
            return await uow.nodes.get_many(node_ids)

    async def _hydrate_parent_contexts(
        self,
        nodes: tuple[IndexNode, ...],
    ) -> dict[str, IndexNode]:
        parent_ids = tuple(
            sorted({node.parent_node_id for node in nodes if node.parent_node_id})
        )
        if not parent_ids:
            return {}

        parent_nodes = await self._hydrate_nodes(parent_ids)
        parents_by_id = {node.node_id: node for node in parent_nodes}
        return {
            node.node_id: parents_by_id[node.parent_node_id]
            for node in nodes
            if node.parent_node_id is not None and node.parent_node_id in parents_by_id
        }

    def _text_collection_names(self) -> tuple[str, ...]:
        return tuple(
            sorted({profile.text_collection for profile in self._profile_registry.list()})
        )

    def _normalize_query_text(self, query: str) -> NormalizedQuery:
        """Normalize query text."""
        if self._query_normalizer:
            return self._query_normalizer.normalize(query)

        # Fallback to basic normalization
        normalized = _normalize_query(query)
        return NormalizedQuery(original=query, normalized=normalized, language=None)

    async def _transform_query(self, query: NormalizedQuery) -> "TransformedQuery":  # noqa: F821
        """Transform query using configured strategy."""
        from ragmax.application.retrieval.query_dtos import TransformedQuery

        if self._query_transformer:
            return await self._query_transformer.transform(query)

        # Fallback: no transformation
        return TransformedQuery(
            original=query.normalized,
            variants=(query.normalized,),
            strategy="original",
            metadata=None,
        )

    async def _vector_search_with_variants(
        self,
        transformed_query: "TransformedQuery",  # noqa: F821
        command: RetrievalCommand,
        top_k: int,
    ) -> tuple[VectorSearchHit, ...]:
        """Perform vector search with query variants."""
        from ragmax.application.retrieval.ports import VectorSearchHit

        all_hits: list[VectorSearchHit] = []
        seen_node_ids: set[str] = set()

        for variant in transformed_query.variants:
            query_vector = (await self._embedding_provider.embed_texts([variant]))[0]
            hits = await self._vector_searcher.search(
                collection_names=self._text_collection_names(),
                query_vector=query_vector,
                notebook_id=command.notebook_id,
                source_ids=command.source_ids,
                content_types=command.content_types,
                limit=top_k,
                score_threshold=command.score_threshold,
            )

            # Deduplicate across variants
            for hit in hits:
                if hit.node_id not in seen_node_ids:
                    all_hits.append(hit)
                    seen_node_ids.add(hit.node_id)

        # Sort by score and limit
        all_hits.sort(key=lambda x: x.score, reverse=True)
        return tuple(all_hits[:top_k])

    async def _bm25_search_with_variants(
        self,
        transformed_query: "TransformedQuery",  # noqa: F821
        command: RetrievalCommand,
        top_k: int,
    ) -> tuple["BM25SearchHit", ...]:  # noqa: F821
        """Perform BM25 search with query variants."""
        from ragmax.application.retrieval.fusion_dtos import BM25SearchHit

        if not self._bm25_searcher:
            return ()

        all_hits: list[BM25SearchHit] = []
        seen_node_ids: set[str] = set()

        for variant in transformed_query.variants:
            hits = await self._bm25_searcher.search(
                query=variant,
                collection_names=self._text_collection_names(),
                notebook_id=command.notebook_id,
                source_ids=command.source_ids,
                content_types=command.content_types,
                limit=top_k,
            )

            # Deduplicate across variants
            for hit in hits:
                if hit.node_id not in seen_node_ids:
                    all_hits.append(hit)
                    seen_node_ids.add(hit.node_id)

        # Sort by score and limit
        all_hits.sort(key=lambda x: x.score, reverse=True)
        return tuple(all_hits[:top_k])

    async def _rerank_answer_nodes(
        self,
        *,
        query: str,
        nodes: tuple[RetrievedNode, ...],
        top_k: int,
    ) -> tuple[RerankedNode, ...]:
        if not nodes:
            return ()

        current_nodes: tuple[RetrievedNode, ...] = nodes
        if "coarse" in self._reranking_stages:
            coarse_nodes = await self._reranker.rerank(
                query=query,
                nodes=current_nodes,
                top_k=min(self._coarse_top_k, len(current_nodes)),
            )
            current_nodes = tuple(item.retrieved_node for item in coarse_nodes)
            if "fine" not in self._reranking_stages:
                return coarse_nodes[: min(top_k, len(coarse_nodes))]

        if "fine" in self._reranking_stages:
            if self._fine_reranker is None:
                raise ConfigurationError("Fine reranker is not configured.")
            return await self._fine_reranker.rerank(
                query=query,
                nodes=current_nodes,
                top_k=min(top_k, len(current_nodes)),
            )

        raise ConfigurationError("No retrieval reranking stage is configured.")

    def _ensure_configured(self) -> None:
        if self._embedding_provider is None or self._vector_searcher is None:
            raise ConfigurationError("Retrieval is not configured.")

    def _ensure_answer_configured(self) -> None:
        if self._reranker is None:
            raise ConfigurationError("Reranker is not configured.")
        if self._answer_generator is None:
            raise ConfigurationError("Answer generation is not configured.")
        if "fine" in self._reranking_stages and self._fine_reranker is None:
            raise ConfigurationError("Fine reranker is not configured.")

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

    def _normalize_configured_top_k(self, value: int, field_name: str) -> int:
        if value < 1:
            raise ConfigurationError(f"{field_name} must be at least 1.")
        return min(value, self._max_top_k)

    def _fine_reranking_enabled(self) -> bool:
        return "fine" in self._reranking_stages

    def _reranker_name(self) -> str:
        if self._fine_reranking_enabled() and self._fine_reranker is not None:
            if "coarse" in self._reranking_stages:
                return f"{self._reranker.name}+{self._fine_reranker.name}"
            return self._fine_reranker.name
        return self._reranker.name


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
        context_node = retrieved_node.context_node or node
        metadata = dict(context_node.metadata)
        metadata["retrieval"] = {
            "rank": reranked_node.rank,
            "vector_score": reranked_node.vector_score,
            "rerank_score": reranked_node.rerank_score,
            "rerank_reason": reranked_node.reason,
            "rerank_metadata": reranked_node.metadata,
            "payload": retrieved_node.payload,
            "matched_node_id": node.node_id,
            "context_node_id": context_node.node_id,
            "expanded_from_parent": context_node.node_id != node.node_id,
        }
        contexts.append(
            RetrievalContextItem(
                context_id=f"ctx_{index}",
                citation_id=str(index),
                node_id=context_node.node_id,
                source_id=context_node.source_id,
                notebook_id=context_node.notebook_id,
                text=context_node.text,
                score=reranked_node.rerank_score,
                vector_score=reranked_node.vector_score,
                rerank_score=reranked_node.rerank_score,
                collection_name=retrieved_node.collection_name,
                content_type=context_node.content_type,
                page_start=context_node.page_start,
                page_end=context_node.page_end,
                section_path=context_node.section_path,
                citation=_citation_from_node(context_node),
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
