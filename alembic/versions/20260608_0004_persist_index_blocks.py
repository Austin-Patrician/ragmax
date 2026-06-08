"""persist parser blocks as indexing artifacts

Revision ID: 20260608_0004
Revises: 20260607_0003
Create Date: 2026-06-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260608_0004"
down_revision: str | None = "20260607_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("sources", "blocks", new_column_name="input_blocks")

    op.create_table(
        "index_blocks",
        sa.Column("block_id", sa.String(length=160), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("notebook_id", sa.String(length=64), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("bbox", sa.JSON(), nullable=True),
        sa.Column("section_hint", sa.JSON(), nullable=False),
        sa.Column("parser_name", sa.String(length=64), nullable=True),
        sa.Column("parser_version", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["index_jobs.job_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.source_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("block_id"),
    )
    op.create_index(op.f("ix_index_blocks_block_type"), "index_blocks", ["block_type"])
    op.create_index(op.f("ix_index_blocks_content_hash"), "index_blocks", ["content_hash"])
    op.create_index(op.f("ix_index_blocks_job_id"), "index_blocks", ["job_id"])
    op.create_index(op.f("ix_index_blocks_notebook_id"), "index_blocks", ["notebook_id"])
    op.create_index(op.f("ix_index_blocks_parser_name"), "index_blocks", ["parser_name"])
    op.create_index(op.f("ix_index_blocks_source_id"), "index_blocks", ["source_id"])
    op.create_index("ix_index_blocks_job_order", "index_blocks", ["job_id", "order_index"])
    op.create_index(
        "ix_index_blocks_source_order",
        "index_blocks",
        ["source_id", "order_index"],
    )
    op.create_index(
        "ix_index_blocks_source_type",
        "index_blocks",
        ["source_id", "block_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_index_blocks_source_type", table_name="index_blocks")
    op.drop_index("ix_index_blocks_source_order", table_name="index_blocks")
    op.drop_index("ix_index_blocks_job_order", table_name="index_blocks")
    op.drop_index(op.f("ix_index_blocks_source_id"), table_name="index_blocks")
    op.drop_index(op.f("ix_index_blocks_parser_name"), table_name="index_blocks")
    op.drop_index(op.f("ix_index_blocks_notebook_id"), table_name="index_blocks")
    op.drop_index(op.f("ix_index_blocks_job_id"), table_name="index_blocks")
    op.drop_index(op.f("ix_index_blocks_content_hash"), table_name="index_blocks")
    op.drop_index(op.f("ix_index_blocks_block_type"), table_name="index_blocks")
    op.drop_table("index_blocks")

    op.alter_column("sources", "input_blocks", new_column_name="blocks")
