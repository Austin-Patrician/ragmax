"""add indexing pipeline runs

Revision ID: 20260609_0007
Revises: 20260608_0006
Create Date: 2026-06-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260609_0007"
down_revision: str | None = "20260608_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "index_pipeline_runs",
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_profile", sa.String(length=64), nullable=True),
        sa.Column("effective_profile", sa.String(length=64), nullable=True),
        sa.Column("requested_parser", sa.String(length=64), nullable=True),
        sa.Column("effective_parser", sa.String(length=64), nullable=True),
        sa.Column("overrides", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.source_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(op.f("ix_index_pipeline_runs_source_id"), "index_pipeline_runs", ["source_id"])
    op.create_index(op.f("ix_index_pipeline_runs_status"), "index_pipeline_runs", ["status"])
    op.create_index(
        "ix_index_pipeline_runs_source_created",
        "index_pipeline_runs",
        ["source_id", "created_at"],
    )

    op.create_table(
        "index_stage_runs",
        sa.Column("stage_run_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("stage_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("stale", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("artifact_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["index_pipeline_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("stage_run_id"),
        sa.UniqueConstraint("run_id", "stage_name", "sequence_no", name="uq_index_stage_run_seq"),
    )
    op.create_index(op.f("ix_index_stage_runs_run_id"), "index_stage_runs", ["run_id"])
    op.create_index(op.f("ix_index_stage_runs_stage_name"), "index_stage_runs", ["stage_name"])
    op.create_index(op.f("ix_index_stage_runs_status"), "index_stage_runs", ["status"])
    op.create_index(op.f("ix_index_stage_runs_stale"), "index_stage_runs", ["stale"])
    op.create_index("ix_index_stage_runs_run_stage", "index_stage_runs", ["run_id", "stage_name"])

    op.create_table(
        "index_artifact_manifests",
        sa.Column("artifact_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("stage_run_id", sa.String(length=64), nullable=False),
        sa.Column("stage_name", sa.String(length=64), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False),
        sa.Column("payload_format", sa.String(length=32), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("preview", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["index_pipeline_runs.run_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["stage_run_id"],
            ["index_stage_runs.stage_run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("artifact_id"),
    )
    op.create_index(
        op.f("ix_index_artifact_manifests_run_id"),
        "index_artifact_manifests",
        ["run_id"],
    )
    op.create_index(
        op.f("ix_index_artifact_manifests_stage_run_id"),
        "index_artifact_manifests",
        ["stage_run_id"],
    )
    op.create_index(
        op.f("ix_index_artifact_manifests_stage_name"),
        "index_artifact_manifests",
        ["stage_name"],
    )
    op.create_index(
        op.f("ix_index_artifact_manifests_artifact_type"),
        "index_artifact_manifests",
        ["artifact_type"],
    )
    op.create_index(
        op.f("ix_index_artifact_manifests_content_hash"),
        "index_artifact_manifests",
        ["content_hash"],
    )
    op.create_index(
        "ix_index_artifact_manifests_run_stage",
        "index_artifact_manifests",
        ["run_id", "stage_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_index_artifact_manifests_run_stage", table_name="index_artifact_manifests")
    op.drop_index(op.f("ix_index_artifact_manifests_content_hash"), table_name="index_artifact_manifests")
    op.drop_index(op.f("ix_index_artifact_manifests_artifact_type"), table_name="index_artifact_manifests")
    op.drop_index(op.f("ix_index_artifact_manifests_stage_name"), table_name="index_artifact_manifests")
    op.drop_index(op.f("ix_index_artifact_manifests_stage_run_id"), table_name="index_artifact_manifests")
    op.drop_index(op.f("ix_index_artifact_manifests_run_id"), table_name="index_artifact_manifests")
    op.drop_table("index_artifact_manifests")

    op.drop_index("ix_index_stage_runs_run_stage", table_name="index_stage_runs")
    op.drop_index(op.f("ix_index_stage_runs_stale"), table_name="index_stage_runs")
    op.drop_index(op.f("ix_index_stage_runs_status"), table_name="index_stage_runs")
    op.drop_index(op.f("ix_index_stage_runs_stage_name"), table_name="index_stage_runs")
    op.drop_index(op.f("ix_index_stage_runs_run_id"), table_name="index_stage_runs")
    op.drop_table("index_stage_runs")

    op.drop_index("ix_index_pipeline_runs_source_created", table_name="index_pipeline_runs")
    op.drop_index(op.f("ix_index_pipeline_runs_status"), table_name="index_pipeline_runs")
    op.drop_index(op.f("ix_index_pipeline_runs_source_id"), table_name="index_pipeline_runs")
    op.drop_table("index_pipeline_runs")
