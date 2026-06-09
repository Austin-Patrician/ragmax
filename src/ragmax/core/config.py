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
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "postgresql+asyncpg://ragmax:ragmax@localhost:5432/ragmax"

    auth_jwt_secret: SecretStr = SecretStr("ragmax-local-development-secret")
    auth_access_token_minutes: int = 15
    auth_refresh_token_days: int = 7
    auth_refresh_cookie_name: str = "ragmax_refresh_token"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_bootstrap_username: str | None = None
    auth_bootstrap_password: SecretStr | None = None
    auth_bootstrap_routes: str = "/files,/datasets,/indexing,/retrieval,/evaluation"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: SecretStr | None = None

    source_storage_dir: Path = Path("storage/sources")
    indexing_artifact_storage_dir: Path = Path("storage/indexing-artifacts")
    max_upload_bytes: int = 50 * 1024 * 1024

    default_file_parser: str = "simple_directory_reader"
    llamaparse_default_tier: str = "agentic"
    llamaparse_default_version: str = "latest"
    llama_cloud_api_key: SecretStr | None = None
    llamaparse_use_vendor_multimodal: bool = True
    llamaparse_vendor_multimodal_model: str = "anthropic-sonnet-4"
    llamaparse_take_screenshot: bool = True

    vector_index_enabled: bool = False
    vector_sparse_index_enabled: bool = True
    embedding_provider: str = "hash"
    embedding_dimension: int = 384
    hash_embedding_model: str = "hash-embedding-v1"
    openai_api_key: SecretStr | None = None
    openai_base_url: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_embedding_batch_size: int = 16

    retrieval_enabled: bool = False
    retrieval_default_top_k: int = 8
    retrieval_max_top_k: int = 100
    retrieval_rerank_default_top_k: int = 8
    retrieval_answer_max_context_items: int = 8
    retrieval_reranker: str = "score_keyword"
    retrieval_answer_generator: str = "extractive"

    # Query Processing
    retrieval_query_transformation: str = "original"
    retrieval_query_multi_query_count: int = 3

    # Hybrid Retrieval (BM25 + Vector)
    retrieval_bm25_enabled: bool = False
    retrieval_bm25_top_k: int = 100
    retrieval_fusion_strategy: str = "rrf"
    retrieval_fusion_rrf_k: int = 60

    # Reranking
    retrieval_reranking_stages: str = "coarse"
    retrieval_reranker_fine: str = "none"
    retrieval_reranker_fine_model: str = "BAAI/bge-reranker-v2-m3"
    retrieval_reranker_fine_device: str = "cpu"
    retrieval_reranker_fine_batch_size: int = 16
    retrieval_reranker_fine_max_length: int = 512
    retrieval_reranker_coarse_top_k: int = 100
    retrieval_reranker_fine_top_k: int = 20

    # Context Building
    retrieval_context_strategy: str = "child_with_parent"
    retrieval_context_max_length: int = 2000
    retrieval_context_deduplication_threshold: float = 0.95

    # LLM Answer Generation
    retrieval_llm_provider: str = "openai"
    retrieval_llm_model: str = "gpt-4o-mini"
    retrieval_llm_base_url: str | None = None
    retrieval_llm_api_key: SecretStr | None = None
    retrieval_llm_temperature: float = 0.0
    retrieval_llm_max_tokens: int = 1000

    # Multi-Query Transformation LLM (separate config)
    retrieval_query_llm_provider: str = "openai"
    retrieval_query_llm_model: str = "gpt-4o-mini"
    retrieval_query_llm_base_url: str | None = None
    retrieval_query_llm_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return _split_csv(self.cors_allowed_origins)

    @property
    def auth_bootstrap_route_list(self) -> list[str]:
        return _split_csv(self.auth_bootstrap_routes)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
