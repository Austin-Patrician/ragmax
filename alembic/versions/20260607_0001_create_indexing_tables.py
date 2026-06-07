"""create indexing tables

Revision ID: 20260607_0001
Revises:
Create Date: 2026-06-07

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260607_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("notebook_id", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("media_type", sa.String(length=128), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("blocks", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_index(op.f("ix_sources_notebook_id"), "sources", ["notebook_id"], unique=False)
    op.create_index(op.f("ix_sources_source_hash"), "sources", ["source_hash"], unique=False)

    op.create_table(
        "index_jobs",
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_profile", sa.String(length=64), nullable=True),
        sa.Column("effective_profile", sa.String(length=64), nullable=True),
        sa.Column("overrides", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.source_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(op.f("ix_index_jobs_source_id"), "index_jobs", ["source_id"], unique=False)
    op.create_index(op.f("ix_index_jobs_status"), "index_jobs", ["status"], unique=False)

    op.create_table(
        "index_nodes",
        sa.Column("node_id", sa.String(length=160), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("notebook_id", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("section_path", sa.JSON(), nullable=False),
        sa.Column("block_ids", sa.JSON(), nullable=False),
        sa.Column("parent_node_id", sa.String(length=160), nullable=True),
        sa.Column("asset_path", sa.String(length=1024), nullable=True),
        sa.Column("bbox", sa.JSON(), nullable=True),
        sa.Column("indexing_profile", sa.String(length=64), nullable=True),
        sa.Column("parser_version", sa.String(length=64), nullable=True),
        sa.Column("chunker_version", sa.String(length=64), nullable=True),
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["index_jobs.job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.source_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id"),
    )
    op.create_index(
        op.f("ix_index_nodes_content_type"),
        "index_nodes",
        ["content_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_index_nodes_indexing_profile"),
        "index_nodes",
        ["indexing_profile"],
        unique=False,
    )
    op.create_index(op.f("ix_index_nodes_job_id"), "index_nodes", ["job_id"], unique=False)
    op.create_index(op.f("ix_index_nodes_modality"), "index_nodes", ["modality"], unique=False)
    op.create_index(
        op.f("ix_index_nodes_notebook_id"),
        "index_nodes",
        ["notebook_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_index_nodes_parent_node_id"),
        "index_nodes",
        ["parent_node_id"],
        unique=False,
    )
    op.create_index(op.f("ix_index_nodes_source_id"), "index_nodes", ["source_id"], unique=False)
    op.create_index(
        "ix_index_nodes_source_content_type",
        "index_nodes",
        ["source_id", "content_type"],
        unique=False,
    )
    op.create_index(
        "ix_index_nodes_notebook_profile",
        "index_nodes",
        ["notebook_id", "indexing_profile"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_index_nodes_notebook_profile", table_name="index_nodes")
    op.drop_index("ix_index_nodes_source_content_type", table_name="index_nodes")
    op.drop_index(op.f("ix_index_nodes_source_id"), table_name="index_nodes")
    op.drop_index(op.f("ix_index_nodes_parent_node_id"), table_name="index_nodes")
    op.drop_index(op.f("ix_index_nodes_notebook_id"), table_name="index_nodes")
    op.drop_index(op.f("ix_index_nodes_modality"), table_name="index_nodes")
    op.drop_index(op.f("ix_index_nodes_job_id"), table_name="index_nodes")
    op.drop_index(op.f("ix_index_nodes_indexing_profile"), table_name="index_nodes")
    op.drop_index(op.f("ix_index_nodes_content_type"), table_name="index_nodes")
    op.drop_table("index_nodes")

    op.drop_index(op.f("ix_index_jobs_status"), table_name="index_jobs")
    op.drop_index(op.f("ix_index_jobs_source_id"), table_name="index_jobs")
    op.drop_table("index_jobs")

    op.drop_index(op.f("ix_sources_source_hash"), table_name="sources")
    op.drop_index(op.f("ix_sources_notebook_id"), table_name="sources")
    op.drop_table("sources")
