"""add datasets tables

Revision ID: 20260609_0008
Revises: 20260609_0007
Create Date: 2026-06-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260609_0008"
down_revision: str | None = "20260609_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create datasets table
    op.create_table(
        "datasets",
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("dataset_id"),
    )
    op.create_index(op.f("ix_datasets_name"), "datasets", ["name"])
    op.create_index(op.f("ix_datasets_created_at"), "datasets", ["created_at"])

    # Create dataset_files association table
    op.create_table(
        "dataset_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["dataset_id"],
            ["datasets.dataset_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.source_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_id", "source_id", name="uq_dataset_files_dataset_source"),
    )
    op.create_index(op.f("ix_dataset_files_dataset_id"), "dataset_files", ["dataset_id"])
    op.create_index(op.f("ix_dataset_files_source_id"), "dataset_files", ["source_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_dataset_files_source_id"), table_name="dataset_files")
    op.drop_index(op.f("ix_dataset_files_dataset_id"), table_name="dataset_files")
    op.drop_table("dataset_files")

    op.drop_index(op.f("ix_datasets_created_at"), table_name="datasets")
    op.drop_index(op.f("ix_datasets_name"), table_name="datasets")
    op.drop_table("datasets")
