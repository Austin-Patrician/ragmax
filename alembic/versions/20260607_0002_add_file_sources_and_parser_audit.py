"""add file sources and parser audit fields

Revision ID: 20260607_0002
Revises: 20260607_0001
Create Date: 2026-06-07

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260607_0002"
down_revision: str | None = "20260607_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("file_path", sa.String(length=1024), nullable=True))
    op.add_column("sources", sa.Column("file_size", sa.Integer(), nullable=True))
    op.add_column(
        "index_jobs",
        sa.Column("requested_parser", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "index_jobs",
        sa.Column("effective_parser", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("index_jobs", "effective_parser")
    op.drop_column("index_jobs", "requested_parser")
    op.drop_column("sources", "file_size")
    op.drop_column("sources", "file_path")
