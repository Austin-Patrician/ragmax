"""add vector index audit fields

Revision ID: 20260607_0003
Revises: 20260607_0002
Create Date: 2026-06-07

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260607_0003"
down_revision: str | None = "20260607_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("index_jobs", sa.Column("vector_status", sa.String(length=32), nullable=True))
    op.add_column("index_jobs", sa.Column("vector_error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("index_jobs", "vector_error_message")
    op.drop_column("index_jobs", "vector_status")
