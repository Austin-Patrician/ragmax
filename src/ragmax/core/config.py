from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    app_name: str = "ragmax"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://ragmax:ragmax@localhost:5432/ragmax"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None

    source_storage_dir: Path = Path("storage/sources")
    max_upload_bytes: int = 50 * 1024 * 1024

    default_file_parser: str = "simple_directory_reader"
    llamaparse_default_tier: str = "agentic"
    llamaparse_default_version: str = "latest"
    llama_cloud_api_key: SecretStr | None = None

    vector_index_enabled: bool = False
    embedding_provider: str = "hash"
    embedding_dimension: int = 384
    hash_embedding_model: str = "hash-embedding-v1"
    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_batch_size: int = 16

    retrieval_enabled: bool = False
    retrieval_default_top_k: int = 8
    retrieval_max_top_k: int = 50
    retrieval_rerank_default_top_k: int = 8
    retrieval_answer_max_context_items: int = 8
    retrieval_reranker: str = "score_keyword"
    retrieval_answer_generator: str = "extractive"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
