"""Add evaluation tables

Revision ID: 20260608_0006
Revises: 20260608_0005
Create Date: 2026-06-08 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260608_0006"
down_revision: Union[str, None] = "20260608_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create eval_datasets table
    op.create_table(
        "eval_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0.0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("name", "version", name="uq_eval_datasets_name_version"),
    )

    # Create eval_test_cases table
    op.create_table(
        "eval_test_cases",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("expected_answer", sa.Text, nullable=True),
        sa.Column("ground_truth_docs", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["dataset_id"], ["eval_datasets.id"], name="fk_eval_test_cases_dataset"),
    )

    # Create eval_experiments table
    op.create_table(
        "eval_experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=False),
        sa.Column("metrics_summary", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["eval_datasets.id"], name="fk_eval_experiments_dataset"),
    )

    # Create eval_results table
    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_case_id", sa.String(255), nullable=False),
        sa.Column("retrieval_result", postgresql.JSONB, nullable=True),
        sa.Column("generation_result", postgresql.JSONB, nullable=True),
        sa.Column("metrics", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("passed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["experiment_id"], ["eval_experiments.id"], name="fk_eval_results_experiment"),
        sa.ForeignKeyConstraint(["test_case_id"], ["eval_test_cases.id"], name="fk_eval_results_test_case"),
    )

    # Create indexes
    op.create_index("idx_eval_test_cases_dataset", "eval_test_cases", ["dataset_id"])
    op.create_index("idx_eval_experiments_dataset", "eval_experiments", ["dataset_id"])
    op.create_index("idx_eval_experiments_started", "eval_experiments", [sa.text("started_at DESC")])
    op.create_index("idx_eval_results_experiment", "eval_results", ["experiment_id"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_eval_results_experiment", table_name="eval_results")
    op.drop_index("idx_eval_experiments_started", table_name="eval_experiments")
    op.drop_index("idx_eval_experiments_dataset", table_name="eval_experiments")
    op.drop_index("idx_eval_test_cases_dataset", table_name="eval_test_cases")

    # Drop tables in reverse order
    op.drop_table("eval_results")
    op.drop_table("eval_experiments")
    op.drop_table("eval_test_cases")
    op.drop_table("eval_datasets")
