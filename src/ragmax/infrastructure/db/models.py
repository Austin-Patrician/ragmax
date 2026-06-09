from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ragmax.infrastructure.db.base import Base

JSONB_SQLITE_JSON = JSONB().with_variant(JSON(), "sqlite")


def utc_now() -> datetime:
    return datetime.now(UTC)


class SourceModel(Base):
    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    notebook_id: Mapped[str] = mapped_column(String(64), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    media_type: Mapped[str] = mapped_column(String(128))
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str | None] = mapped_column(Text)
    input_blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    file_path: Mapped[str | None] = mapped_column(String(1024))
    file_size: Mapped[int | None] = mapped_column(Integer)
    source_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserModel(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


# Evaluation platform models


class EvalDatasetModel(Base):
    __tablename__ = "eval_datasets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(50), nullable=False, server_default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (UniqueConstraint("name", "version", name="uq_eval_datasets_name_version"),)


class EvalTestCaseModel(Base):
    __tablename__ = "eval_test_cases"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    dataset_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("eval_datasets.id"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str | None] = mapped_column(Text)
    ground_truth_docs: Mapped[list[str]] = mapped_column(
        JSONB_SQLITE_JSON, nullable=False, server_default="[]"
    )
    test_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB_SQLITE_JSON, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("idx_eval_test_cases_dataset", "dataset_id"),)


class EvalExperimentModel(Base):
    __tablename__ = "eval_experiments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("eval_datasets.id"), nullable=False
    )
    config: Mapped[dict[str, Any]] = mapped_column(JSONB_SQLITE_JSON, nullable=False)
    metrics_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB_SQLITE_JSON)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        Index("idx_eval_experiments_dataset", "dataset_id"),
        Index("idx_eval_experiments_started", "started_at"),
    )


class EvalResultModel(Base):
    __tablename__ = "eval_results"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    experiment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("eval_experiments.id"), nullable=False
    )
    test_case_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("eval_test_cases.id"), nullable=False
    )
    retrieval_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB_SQLITE_JSON)
    generation_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB_SQLITE_JSON)
    metrics: Mapped[dict[str, float]] = mapped_column(
        JSONB_SQLITE_JSON, nullable=False, server_default="{}"
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (Index("idx_eval_results_experiment", "experiment_id"),)


class UserRoutePermissionModel(Base):
    __tablename__ = "user_route_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "route_path", name="uq_user_route_permissions_user_route"),
    )

    permission_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        index=True,
    )
    route_path: Mapped[str] = mapped_column(String(256), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AppRuntimeConfigurationModel(Base):
    __tablename__ = "app_runtime_configuration"

    config_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_storage_dir: Mapped[str | None] = mapped_column(String(1024))
    indexing_artifact_storage_dir: Mapped[str | None] = mapped_column(String(1024))
    max_upload_bytes: Mapped[int | None] = mapped_column(Integer)
    default_file_parser: Mapped[str | None] = mapped_column(String(64))
    llamaparse_default_tier: Mapped[str | None] = mapped_column(String(64))
    llamaparse_default_version: Mapped[str | None] = mapped_column(String(64))
    llama_cloud_api_key: Mapped[str | None] = mapped_column(Text)
    llamaparse_use_vendor_multimodal: Mapped[bool | None] = mapped_column(Boolean)
    llamaparse_vendor_multimodal_model: Mapped[str | None] = mapped_column(String(128))
    llamaparse_take_screenshot: Mapped[bool | None] = mapped_column(Boolean)
    vector_index_enabled: Mapped[bool | None] = mapped_column(Boolean)
    vector_sparse_index_enabled: Mapped[bool | None] = mapped_column(Boolean)
    qdrant_url: Mapped[str | None] = mapped_column(String(512))
    qdrant_api_key: Mapped[str | None] = mapped_column(Text)
    retrieval_enabled: Mapped[bool | None] = mapped_column(Boolean)
    retrieval_default_top_k: Mapped[int | None] = mapped_column(Integer)
    retrieval_max_top_k: Mapped[int | None] = mapped_column(Integer)
    retrieval_rerank_default_top_k: Mapped[int | None] = mapped_column(Integer)
    retrieval_answer_max_context_items: Mapped[int | None] = mapped_column(Integer)
    retrieval_reranker: Mapped[str | None] = mapped_column(String(64))
    retrieval_answer_generator: Mapped[str | None] = mapped_column(String(64))
    retrieval_query_transformation: Mapped[str | None] = mapped_column(String(64))
    retrieval_query_multi_query_count: Mapped[int | None] = mapped_column(Integer)
    retrieval_bm25_enabled: Mapped[bool | None] = mapped_column(Boolean)
    retrieval_bm25_top_k: Mapped[int | None] = mapped_column(Integer)
    retrieval_fusion_strategy: Mapped[str | None] = mapped_column(String(64))
    retrieval_fusion_rrf_k: Mapped[int | None] = mapped_column(Integer)
    retrieval_reranking_stages: Mapped[str | None] = mapped_column(String(128))
    retrieval_reranker_fine_device: Mapped[str | None] = mapped_column(String(64))
    retrieval_reranker_fine_batch_size: Mapped[int | None] = mapped_column(Integer)
    retrieval_reranker_fine_max_length: Mapped[int | None] = mapped_column(Integer)
    retrieval_reranker_coarse_top_k: Mapped[int | None] = mapped_column(Integer)
    retrieval_reranker_fine_top_k: Mapped[int | None] = mapped_column(Integer)
    retrieval_context_strategy: Mapped[str | None] = mapped_column(String(64))
    retrieval_context_max_length: Mapped[int | None] = mapped_column(Integer)
    retrieval_context_deduplication_threshold: Mapped[float | None] = mapped_column(Float)
    retrieval_llm_temperature: Mapped[float | None] = mapped_column(Float)
    retrieval_llm_max_tokens: Mapped[int | None] = mapped_column(Integer)
    openai_embedding_batch_size: Mapped[int | None] = mapped_column(Integer)
    updated_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ModelProviderModel(Base):
    __tablename__ = "model_providers"
    __table_args__ = (UniqueConstraint("name", name="uq_model_providers_name"),)

    provider_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    provider_type: Mapped[str] = mapped_column(String(64), index=True)
    base_url: Mapped[str | None] = mapped_column(String(512))
    api_key: Mapped[str | None] = mapped_column(Text)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProviderModelModel(Base):
    __tablename__ = "provider_models"
    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "model_name",
            "ai_type",
            name="uq_provider_models_provider_name_type",
        ),
        Index("ix_provider_models_provider_type", "provider_id", "ai_type"),
    )

    model_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("model_providers.provider_id", ondelete="CASCADE"),
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    ai_type: Mapped[str] = mapped_column(String(32), index=True)
    dimension: Mapped[int | None] = mapped_column(Integer)
    context_window: Mapped[int | None] = mapped_column(Integer)
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ModelDefaultBindingModel(Base):
    __tablename__ = "model_default_bindings"

    binding_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("provider_models.model_id", ondelete="CASCADE"),
        index=True,
    )
    updated_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuthRefreshSessionModel(Base):
    __tablename__ = "auth_refresh_sessions"
    __table_args__ = (
        Index("ix_auth_refresh_sessions_user_active", "user_id", "revoked_at"),
    )

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IndexJobModel(Base):
    __tablename__ = "index_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sources.source_id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    requested_profile: Mapped[str | None] = mapped_column(String(64))
    effective_profile: Mapped[str | None] = mapped_column(String(64))
    requested_parser: Mapped[str | None] = mapped_column(String(64))
    effective_parser: Mapped[str | None] = mapped_column(String(64))
    overrides: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    vector_status: Mapped[str | None] = mapped_column(String(32))
    vector_error_message: Mapped[str | None] = mapped_column(Text)
    node_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IndexPipelineRunModel(Base):
    __tablename__ = "index_pipeline_runs"
    __table_args__ = (
        Index("ix_index_pipeline_runs_source_created", "source_id", "created_at"),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sources.source_id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    requested_profile: Mapped[str | None] = mapped_column(String(64))
    effective_profile: Mapped[str | None] = mapped_column(String(64))
    requested_parser: Mapped[str | None] = mapped_column(String(64))
    effective_parser: Mapped[str | None] = mapped_column(String(64))
    overrides: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IndexStageRunModel(Base):
    __tablename__ = "index_stage_runs"
    __table_args__ = (
        UniqueConstraint("run_id", "stage_name", "sequence_no", name="uq_index_stage_run_seq"),
        Index("ix_index_stage_runs_run_stage", "run_id", "stage_name"),
    )

    stage_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("index_pipeline_runs.run_id", ondelete="CASCADE"),
        index=True,
    )
    stage_name: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    stale: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float | None] = mapped_column(Float)
    artifact_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IndexArtifactManifestModel(Base):
    __tablename__ = "index_artifact_manifests"
    __table_args__ = (
        Index("ix_index_artifact_manifests_run_stage", "run_id", "stage_name"),
    )

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("index_pipeline_runs.run_id", ondelete="CASCADE"),
        index=True,
    )
    stage_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("index_stage_runs.stage_run_id", ondelete="CASCADE"),
        index=True,
    )
    stage_name: Mapped[str] = mapped_column(String(64), index=True)
    artifact_type: Mapped[str] = mapped_column(String(64), index=True)
    storage_uri: Mapped[str] = mapped_column(String(1024))
    payload_format: Mapped[str] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    record_count: Mapped[int] = mapped_column(Integer)
    preview: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IndexBlockModel(Base):
    __tablename__ = "index_blocks"
    __table_args__ = (
        Index("ix_index_blocks_source_order", "source_id", "order_index"),
        Index("ix_index_blocks_job_order", "job_id", "order_index"),
        Index("ix_index_blocks_source_type", "source_id", "block_type"),
    )

    block_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("index_jobs.job_id", ondelete="CASCADE"),
        index=True,
    )
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sources.source_id", ondelete="CASCADE"),
        index=True,
    )
    notebook_id: Mapped[str] = mapped_column(String(64), index=True)
    order_index: Mapped[int] = mapped_column(Integer)
    block_type: Mapped[str] = mapped_column(String(32), index=True)
    text: Mapped[str] = mapped_column(Text)
    page_no: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[list[float] | None] = mapped_column(JSON)
    section_hint: Mapped[list[str]] = mapped_column(JSON, default=list)
    parser_name: Mapped[str | None] = mapped_column(String(64), index=True)
    parser_version: Mapped[str | None] = mapped_column(String(128))
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    block_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IndexNodeModel(Base):
    __tablename__ = "index_nodes"
    __table_args__ = (
        Index("ix_index_nodes_source_content_type", "source_id", "content_type"),
        Index("ix_index_nodes_notebook_profile", "notebook_id", "indexing_profile"),
    )

    node_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    job_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("index_jobs.job_id", ondelete="CASCADE"),
        index=True,
    )
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sources.source_id", ondelete="CASCADE"),
        index=True,
    )
    notebook_id: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    modality: Mapped[str] = mapped_column(String(32), index=True)
    content_type: Mapped[str] = mapped_column(String(64), index=True)
    page_start: Mapped[int | None] = mapped_column(Integer)
    page_end: Mapped[int | None] = mapped_column(Integer)
    section_path: Mapped[list[str]] = mapped_column(JSON, default=list)
    block_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    parent_node_id: Mapped[str | None] = mapped_column(String(160), index=True)
    asset_path: Mapped[str | None] = mapped_column(String(1024))
    bbox: Mapped[list[float] | None] = mapped_column(JSON)
    indexing_profile: Mapped[str | None] = mapped_column(String(64), index=True)
    parser_version: Mapped[str | None] = mapped_column(String(64))
    chunker_version: Mapped[str | None] = mapped_column(String(64))
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    node_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DatasetModel(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    dataset_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DatasetFileModel(Base):
    __tablename__ = "dataset_files"
    __table_args__ = (
        UniqueConstraint("dataset_id", "source_id", name="uq_dataset_files_dataset_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("datasets.dataset_id", ondelete="CASCADE"),
        index=True,
    )
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sources.source_id", ondelete="CASCADE"),
        index=True,
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
