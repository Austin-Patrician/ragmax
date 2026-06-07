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
from ragmax.infrastructure.storage.local_source_storage import LocalSourceStorage


@lru_cache
def get_indexing_service() -> IndexingService:
    return create_indexing_service()


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
            dimension=resolved_settings.embedding_dimension,
        )
    raise ConfigurationError(f"Unsupported embedding provider: {provider}")
