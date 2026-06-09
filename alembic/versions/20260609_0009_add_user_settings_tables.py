"""add user settings and model provider tables

Revision ID: 20260609_0009
Revises: 20260609_0008
Create Date: 2026-06-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260609_0009"
down_revision: str | None = "20260609_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_runtime_configuration",
        sa.Column("config_id", sa.String(length=32), nullable=False),
        sa.Column("source_storage_dir", sa.String(length=1024), nullable=True),
        sa.Column("indexing_artifact_storage_dir", sa.String(length=1024), nullable=True),
        sa.Column("max_upload_bytes", sa.Integer(), nullable=True),
        sa.Column("default_file_parser", sa.String(length=64), nullable=True),
        sa.Column("llamaparse_default_tier", sa.String(length=64), nullable=True),
        sa.Column("llamaparse_default_version", sa.String(length=64), nullable=True),
        sa.Column("llama_cloud_api_key", sa.Text(), nullable=True),
        sa.Column("llamaparse_use_vendor_multimodal", sa.Boolean(), nullable=True),
        sa.Column("llamaparse_vendor_multimodal_model", sa.String(length=128), nullable=True),
        sa.Column("llamaparse_take_screenshot", sa.Boolean(), nullable=True),
        sa.Column("vector_index_enabled", sa.Boolean(), nullable=True),
        sa.Column("vector_sparse_index_enabled", sa.Boolean(), nullable=True),
        sa.Column("qdrant_url", sa.String(length=512), nullable=True),
        sa.Column("qdrant_api_key", sa.Text(), nullable=True),
        sa.Column("retrieval_enabled", sa.Boolean(), nullable=True),
        sa.Column("retrieval_default_top_k", sa.Integer(), nullable=True),
        sa.Column("retrieval_max_top_k", sa.Integer(), nullable=True),
        sa.Column("retrieval_rerank_default_top_k", sa.Integer(), nullable=True),
        sa.Column("retrieval_answer_max_context_items", sa.Integer(), nullable=True),
        sa.Column("retrieval_reranker", sa.String(length=64), nullable=True),
        sa.Column("retrieval_answer_generator", sa.String(length=64), nullable=True),
        sa.Column("retrieval_query_transformation", sa.String(length=64), nullable=True),
        sa.Column("retrieval_query_multi_query_count", sa.Integer(), nullable=True),
        sa.Column("retrieval_bm25_enabled", sa.Boolean(), nullable=True),
        sa.Column("retrieval_bm25_top_k", sa.Integer(), nullable=True),
        sa.Column("retrieval_fusion_strategy", sa.String(length=64), nullable=True),
        sa.Column("retrieval_fusion_rrf_k", sa.Integer(), nullable=True),
        sa.Column("retrieval_reranking_stages", sa.String(length=128), nullable=True),
        sa.Column("retrieval_reranker_fine_device", sa.String(length=64), nullable=True),
        sa.Column("retrieval_reranker_fine_batch_size", sa.Integer(), nullable=True),
        sa.Column("retrieval_reranker_fine_max_length", sa.Integer(), nullable=True),
        sa.Column("retrieval_reranker_coarse_top_k", sa.Integer(), nullable=True),
        sa.Column("retrieval_reranker_fine_top_k", sa.Integer(), nullable=True),
        sa.Column("retrieval_context_strategy", sa.String(length=64), nullable=True),
        sa.Column("retrieval_context_max_length", sa.Integer(), nullable=True),
        sa.Column("retrieval_context_deduplication_threshold", sa.Float(), nullable=True),
        sa.Column("retrieval_llm_temperature", sa.Float(), nullable=True),
        sa.Column("retrieval_llm_max_tokens", sa.Integer(), nullable=True),
        sa.Column("openai_embedding_batch_size", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("config_id"),
    )

    op.create_table(
        "model_providers",
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("provider_id"),
        sa.UniqueConstraint("name", name="uq_model_providers_name"),
    )
    op.create_index(op.f("ix_model_providers_is_enabled"), "model_providers", ["is_enabled"])
    op.create_index(op.f("ix_model_providers_name"), "model_providers", ["name"])
    op.create_index(
        op.f("ix_model_providers_provider_type"),
        "model_providers",
        ["provider_type"],
    )

    op.create_table(
        "provider_models",
        sa.Column("model_id", sa.String(length=64), nullable=False),
        sa.Column("provider_id", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("ai_type", sa.String(length=32), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=True),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["model_providers.provider_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("model_id"),
        sa.UniqueConstraint(
            "provider_id",
            "model_name",
            "ai_type",
            name="uq_provider_models_provider_name_type",
        ),
    )
    op.create_index(op.f("ix_provider_models_ai_type"), "provider_models", ["ai_type"])
    op.create_index(op.f("ix_provider_models_is_enabled"), "provider_models", ["is_enabled"])
    op.create_index(op.f("ix_provider_models_model_name"), "provider_models", ["model_name"])
    op.create_index(
        "ix_provider_models_provider_type",
        "provider_models",
        ["provider_id", "ai_type"],
    )
    op.create_index(op.f("ix_provider_models_provider_id"), "provider_models", ["provider_id"])

    op.create_table(
        "model_default_bindings",
        sa.Column("binding_key", sa.String(length=64), nullable=False),
        sa.Column("model_id", sa.String(length=64), nullable=False),
        sa.Column("updated_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["provider_models.model_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("binding_key"),
    )
    op.create_index(
        op.f("ix_model_default_bindings_model_id"),
        "model_default_bindings",
        ["model_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_model_default_bindings_model_id"), table_name="model_default_bindings")
    op.drop_table("model_default_bindings")

    op.drop_index(op.f("ix_provider_models_provider_id"), table_name="provider_models")
    op.drop_index("ix_provider_models_provider_type", table_name="provider_models")
    op.drop_index(op.f("ix_provider_models_model_name"), table_name="provider_models")
    op.drop_index(op.f("ix_provider_models_is_enabled"), table_name="provider_models")
    op.drop_index(op.f("ix_provider_models_ai_type"), table_name="provider_models")
    op.drop_table("provider_models")

    op.drop_index(op.f("ix_model_providers_provider_type"), table_name="model_providers")
    op.drop_index(op.f("ix_model_providers_name"), table_name="model_providers")
    op.drop_index(op.f("ix_model_providers_is_enabled"), table_name="model_providers")
    op.drop_table("model_providers")

    op.drop_table("app_runtime_configuration")
