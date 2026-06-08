from collections.abc import Callable
from functools import lru_cache

from ragmax.application.indexing.parser_registry import ParserSpec, SourceParserRegistry
from ragmax.application.indexing.ports import (
    EmbeddingProvider,
    IndexingUnitOfWork,
    VectorIndexWriter,
)
from ragmax.application.indexing.profiles import list_indexing_profiles
from ragmax.application.indexing.registry import IndexingProfileRegistry
from ragmax.application.indexing.service import IndexingService
from ragmax.application.retrieval.fusion_ports import BM25Searcher, SearchFuser
from ragmax.application.retrieval.ports import AnswerGenerator, Reranker, VectorSearcher
from ragmax.application.retrieval.service import RetrievalService
from ragmax.core.config import Settings, get_settings
from ragmax.core.exceptions import ConfigurationError
from ragmax.infrastructure.db.repositories.indexing import SqlAlchemyIndexingUnitOfWork
from ragmax.infrastructure.db.session import SessionLocal
from ragmax.infrastructure.indexing.analyzers.heuristic_source_analyzer import (
    HeuristicSourceAnalyzer,
)
from ragmax.infrastructure.indexing.chunkers.ocr_chunker import OcrPageChunker
from ragmax.infrastructure.indexing.chunkers.section_chunker import SectionAwareChunker
from ragmax.infrastructure.indexing.chunkers.sentence_chunker import SentenceChunker
from ragmax.infrastructure.indexing.chunkers.table_chunker import TableAwareChunker
from ragmax.infrastructure.indexing.embeddings.hash_embedding_provider import HashEmbeddingProvider
from ragmax.infrastructure.indexing.embeddings.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)
from ragmax.infrastructure.indexing.enrichers.basic_node_enricher import BasicNodeEnricher
from ragmax.infrastructure.indexing.parsers.heuristic_source_parser import HeuristicSourceParser
from ragmax.infrastructure.indexing.parsers.llamaparse_parser import (
    LLAMAPARSE_EXTENSIONS,
    LlamaParseSourceParser,
)
from ragmax.infrastructure.indexing.parsers.simple_directory_reader_parser import (
    SIMPLE_DIRECTORY_READER_EXTENSIONS,
    SimpleDirectoryReaderSourceParser,
)
from ragmax.infrastructure.qdrant.client import create_qdrant_client
from ragmax.infrastructure.qdrant.vector_index_writer import QdrantVectorIndexWriter
from ragmax.infrastructure.qdrant.vector_searcher import QdrantVectorSearcher
from ragmax.infrastructure.retrieval.answer_generators.extractive_answer_generator import (
    ExtractiveAnswerGenerator,
)
from ragmax.infrastructure.retrieval.rerankers.score_keyword_reranker import (
    ScoreKeywordReranker,
)
from ragmax.infrastructure.storage.local_source_storage import LocalSourceStorage


@lru_cache
def get_indexing_service() -> IndexingService:
    return create_indexing_service()


@lru_cache
def get_retrieval_service() -> RetrievalService:
    return create_retrieval_service()


def create_indexing_service(
    unit_of_work_factory: Callable[[], IndexingUnitOfWork] | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    vector_index_writer: VectorIndexWriter | None = None,
) -> IndexingService:
    settings = get_settings()
    if settings.vector_index_enabled:
        embedding_provider = embedding_provider or create_embedding_provider(settings)
        vector_index_writer = vector_index_writer or QdrantVectorIndexWriter(
            client=create_qdrant_client(settings),
            vector_size=embedding_provider.dimension,
            sparse_index_enabled=settings.vector_sparse_index_enabled,
        )
    elif (embedding_provider is None) != (vector_index_writer is None):
        raise ConfigurationError(
            "embedding_provider and vector_index_writer must be configured together."
        )

    registry = IndexingProfileRegistry(list_indexing_profiles())
    llama_cloud_api_key = (
        settings.llama_cloud_api_key.get_secret_value()
        if settings.llama_cloud_api_key is not None
        else None
    )
    source_parser_registry = SourceParserRegistry(
        parsers={
            "inline_content_parser": HeuristicSourceParser(),
            "simple_directory_reader": SimpleDirectoryReaderSourceParser(),
            "llamaparse": LlamaParseSourceParser(
                api_key=llama_cloud_api_key,
                default_tier=settings.llamaparse_default_tier,
                default_version=settings.llamaparse_default_version,
            ),
        },
        specs=(
            ParserSpec(
                name="simple_directory_reader",
                description="Local LlamaIndex SimpleDirectoryReader parser for common files.",
                supported_extensions=SIMPLE_DIRECTORY_READER_EXTENSIONS,
                supported_media_types=(
                    "application/pdf",
                    "text/plain",
                    "text/markdown",
                    "text/csv",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "image/jpeg",
                    "image/png",
                ),
                is_default=settings.default_file_parser == "simple_directory_reader",
            ),
            ParserSpec(
                name="llamaparse",
                description=(
                    "LlamaParse parser for complex documents, tables, OCR, and rich layouts."
                ),
                supported_extensions=LLAMAPARSE_EXTENSIONS,
                supported_media_types=(
                    "application/pdf",
                    "text/plain",
                    "text/markdown",
                    "text/csv",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "image/jpeg",
                    "image/png",
                    "text/html",
                    "audio/mpeg",
                    "audio/wav",
                ),
                requires_api_key=True,
                is_default=settings.default_file_parser == "llamaparse",
            ),
            ParserSpec(
                name="inline_content_parser",
                description="Internal parser for request text and pre-parsed blocks.",
                is_internal=True,
            ),
        ),
        default_file_parser=settings.default_file_parser,
        inline_parser="inline_content_parser",
    )
    return IndexingService(
        source_parser_registry=source_parser_registry,
        source_analyzer=HeuristicSourceAnalyzer(),
        profile_registry=registry,
        chunkers={
            "sentence_splitter": SentenceChunker(),
            "section_aware": SectionAwareChunker(),
            "table_aware": TableAwareChunker(),
            "ocr_page": OcrPageChunker(),
        },
        node_enricher=BasicNodeEnricher(),
        embedding_provider=embedding_provider,
        vector_index_writer=vector_index_writer,
        unit_of_work_factory=unit_of_work_factory
        or (lambda: SqlAlchemyIndexingUnitOfWork(SessionLocal)),
    )


def create_retrieval_service(
    unit_of_work_factory: Callable[[], IndexingUnitOfWork] | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    vector_searcher: VectorSearcher | None = None,
    bm25_searcher: BM25Searcher | None = None,
    search_fuser: SearchFuser | None = None,
    reranker: Reranker | None = None,
    fine_reranker: Reranker | None = None,
    answer_generator: AnswerGenerator | None = None,
) -> RetrievalService:
    settings = get_settings()
    reranking_stages = _parse_reranking_stages(settings.retrieval_reranking_stages)

    # Query processing
    query_normalizer = None
    query_transformer = None
    if settings.retrieval_enabled:
        from ragmax.infrastructure.retrieval.query.normalizer import BasicQueryNormalizer

        query_normalizer = BasicQueryNormalizer()

        # Query transformer (if not "original")
        if settings.retrieval_query_transformation != "original":
            llm_client = None
            try:
                # Use separate LLM client for query transformation
                llm_client = create_query_llm_client(settings)
            except Exception:
                pass  # LLM not available, fallback to original

            if llm_client:
                from ragmax.infrastructure.retrieval.query.transformer import (
                    create_query_transformer,
                )

                query_transformer = create_query_transformer(
                    strategy=settings.retrieval_query_transformation,
                    llm_client=llm_client,
                    num_variants=settings.retrieval_query_multi_query_count,
                )

    # Core retrieval components
    if settings.retrieval_enabled:
        embedding_provider = embedding_provider or create_embedding_provider(settings)
        vector_searcher = vector_searcher or QdrantVectorSearcher(
            client=create_qdrant_client(settings)
        )

        # BM25 + Fusion (if enabled)
        if settings.retrieval_bm25_enabled:
            from ragmax.infrastructure.qdrant.sparse_searcher import QdrantSparseBM25Searcher
            from ragmax.infrastructure.retrieval.fusion.rrf_fuser import RRFFuser

            bm25_searcher = bm25_searcher or QdrantSparseBM25Searcher(
                client=create_qdrant_client(settings)
            )

            if settings.retrieval_fusion_strategy == "rrf":
                search_fuser = search_fuser or RRFFuser(k=settings.retrieval_fusion_rrf_k)
            else:
                raise ConfigurationError(
                    f"Unsupported retrieval fusion strategy: {settings.retrieval_fusion_strategy}"
                )

    elif (embedding_provider is None) != (vector_searcher is None):
        raise ConfigurationError(
            "embedding_provider and vector_searcher must be configured together."
        )

    reranker = reranker or create_reranker(settings)
    if "fine" in reranking_stages:
        fine_reranker = fine_reranker or create_fine_reranker(settings)
        if fine_reranker is None:
            raise ConfigurationError(
                "Fine reranking is enabled but RETRIEVAL_RERANKER_FINE is none."
            )
    answer_generator = answer_generator or create_answer_generator(settings)

    return RetrievalService(
        embedding_provider=embedding_provider,
        vector_searcher=vector_searcher,
        reranker=reranker,
        fine_reranker=fine_reranker,
        answer_generator=answer_generator,
        profile_registry=IndexingProfileRegistry(list_indexing_profiles()),
        unit_of_work_factory=unit_of_work_factory
        or (lambda: SqlAlchemyIndexingUnitOfWork(SessionLocal)),
        default_top_k=settings.retrieval_default_top_k,
        max_top_k=settings.retrieval_max_top_k,
        default_rerank_top_k=settings.retrieval_rerank_default_top_k,
        bm25_top_k=settings.retrieval_bm25_top_k,
        reranking_stages=reranking_stages,
        coarse_top_k=settings.retrieval_reranker_coarse_top_k,
        fine_top_k=settings.retrieval_reranker_fine_top_k,
        max_context_items=settings.retrieval_answer_max_context_items,
        query_normalizer=query_normalizer,
        query_transformer=query_transformer,
        bm25_searcher=bm25_searcher,
        search_fuser=search_fuser,
    )


@lru_cache
def get_source_storage() -> LocalSourceStorage:
    settings = get_settings()
    return LocalSourceStorage(
        root_dir=settings.source_storage_dir,
        max_upload_bytes=settings.max_upload_bytes,
    )


def create_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    resolved_settings = settings or get_settings()
    provider = resolved_settings.embedding_provider.lower()
    if provider == "hash":
        return HashEmbeddingProvider(
            model_name=resolved_settings.hash_embedding_model,
            dimension=resolved_settings.embedding_dimension,
        )
    if provider == "openai":
        api_key = (
            resolved_settings.openai_api_key.get_secret_value()
            if resolved_settings.openai_api_key is not None
            else None
        )
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            model_name=resolved_settings.openai_embedding_model,
            base_url=resolved_settings.openai_base_url,
            dimension=resolved_settings.embedding_dimension,
            batch_size=resolved_settings.openai_embedding_batch_size,
        )
    raise ConfigurationError(f"Unsupported embedding provider: {provider}")


def create_reranker(settings: Settings | None = None) -> Reranker:
    resolved_settings = settings or get_settings()
    reranker = resolved_settings.retrieval_reranker.lower()
    if reranker == "score_keyword":
        return ScoreKeywordReranker()
    raise ConfigurationError(f"Unsupported retrieval reranker: {reranker}")


def create_fine_reranker(settings: Settings | None = None) -> Reranker | None:
    """Create fine reranker if configured."""
    resolved_settings = settings or get_settings()
    fine_reranker = resolved_settings.retrieval_reranker_fine.lower()

    if fine_reranker == "none":
        return None

    if fine_reranker == "bge":
        from ragmax.infrastructure.retrieval.rerankers.bge_reranker import (
            BGECrossEncoderReranker,
        )

        return BGECrossEncoderReranker(
            model_name=resolved_settings.retrieval_reranker_fine_model,
            device=resolved_settings.retrieval_reranker_fine_device,
            batch_size=resolved_settings.retrieval_reranker_fine_batch_size,
            max_length=resolved_settings.retrieval_reranker_fine_max_length,
        )

    raise ConfigurationError(f"Unsupported fine reranker: {fine_reranker}")


def _parse_reranking_stages(value: str) -> tuple[str, ...]:
    stages = tuple(stage.strip().lower() for stage in value.split(",") if stage.strip())
    if not stages:
        raise ConfigurationError("RETRIEVAL_RERANKING_STAGES must not be empty.")

    supported = {"coarse", "fine"}
    unsupported = sorted(set(stages) - supported)
    if unsupported:
        raise ConfigurationError(
            f"Unsupported retrieval reranking stage(s): {', '.join(unsupported)}"
        )
    return stages


def create_answer_generator(settings: Settings | None = None) -> AnswerGenerator:
    resolved_settings = settings or get_settings()
    generator = resolved_settings.retrieval_answer_generator.lower()
    if generator == "extractive":
        return ExtractiveAnswerGenerator(
            max_contexts=resolved_settings.retrieval_answer_max_context_items
        )
    if generator == "llm":
        llm_client = create_llm_client(resolved_settings)
        from ragmax.infrastructure.retrieval.answer_generators.llm_answer_generator import (
            LLMAnswerGenerator,
        )

        return LLMAnswerGenerator(
            llm_client=llm_client,
            max_context_items=resolved_settings.retrieval_answer_max_context_items,
            temperature=resolved_settings.retrieval_llm_temperature,
            max_tokens=resolved_settings.retrieval_llm_max_tokens,
        )
    raise ConfigurationError(f"Unsupported retrieval answer generator: {generator}")


def create_llm_client(settings: Settings) -> "LLMClient":  # noqa: F821
    """Create LLM client for answer generation."""
    from ragmax.infrastructure.llm.client import OpenAILLMClient

    provider = settings.retrieval_llm_provider.lower()
    if provider == "openai":
        # Use retrieval_llm_api_key if provided, fallback to openai_api_key
        api_key = None
        if settings.retrieval_llm_api_key is not None:
            api_key = settings.retrieval_llm_api_key.get_secret_value()
        elif settings.openai_api_key is not None:
            api_key = settings.openai_api_key.get_secret_value()

        # Use retrieval_llm_base_url if provided, fallback to openai_base_url
        base_url = settings.retrieval_llm_base_url or settings.openai_base_url

        return OpenAILLMClient(
            api_key=api_key,
            model=settings.retrieval_llm_model,
            base_url=base_url,
        )
    raise ConfigurationError(f"Unsupported LLM provider: {provider}")


def create_query_llm_client(settings: Settings) -> "LLMClient":  # noqa: F821
    """Create LLM client for query transformation (Multi-Query, HyDE, etc.).

    This uses separate configuration from answer generation LLM,
    allowing you to use a cheaper/faster model for query expansion.
    """
    from ragmax.infrastructure.llm.client import OpenAILLMClient

    provider = settings.retrieval_query_llm_provider.lower()
    if provider == "openai":
        # Use retrieval_query_llm_api_key if provided, fallback to openai_api_key
        api_key = None
        if settings.retrieval_query_llm_api_key is not None:
            api_key = settings.retrieval_query_llm_api_key.get_secret_value()
        elif settings.openai_api_key is not None:
            api_key = settings.openai_api_key.get_secret_value()

        # Use retrieval_query_llm_base_url if provided, fallback to openai_base_url
        base_url = settings.retrieval_query_llm_base_url or settings.openai_base_url

        return OpenAILLMClient(
            api_key=api_key,
            model=settings.retrieval_query_llm_model,
            base_url=base_url,
        )
    raise ConfigurationError(f"Unsupported query LLM provider: {provider}")
