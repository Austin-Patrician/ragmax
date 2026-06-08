"""add user auth and route permissions

Revision ID: 20260608_0005
Revises: 20260608_0004
Create Date: 2026-06-08

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260608_0005"
down_revision: str | None = "20260608_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_users_is_active"), "users", ["is_active"])
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "user_route_permissions",
        sa.Column("permission_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("route_path", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("permission_id"),
        sa.UniqueConstraint(
            "user_id",
            "route_path",
            name="uq_user_route_permissions_user_route",
        ),
    )
    op.create_index(
        op.f("ix_user_route_permissions_route_path"),
        "user_route_permissions",
        ["route_path"],
    )
    op.create_index(
        op.f("ix_user_route_permissions_user_id"),
        "user_route_permissions",
        ["user_id"],
    )

    op.create_table(
        "auth_refresh_sessions",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(
        op.f("ix_auth_refresh_sessions_expires_at"),
        "auth_refresh_sessions",
        ["expires_at"],
    )
    op.create_index(
        op.f("ix_auth_refresh_sessions_token_hash"),
        "auth_refresh_sessions",
        ["token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_auth_refresh_sessions_user_active",
        "auth_refresh_sessions",
        ["user_id", "revoked_at"],
    )
    op.create_index(
        op.f("ix_auth_refresh_sessions_user_id"),
        "auth_refresh_sessions",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_refresh_sessions_user_id"), table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_user_active", table_name="auth_refresh_sessions")
    op.drop_index(
        op.f("ix_auth_refresh_sessions_token_hash"),
        table_name="auth_refresh_sessions",
    )
    op.drop_index(
        op.f("ix_auth_refresh_sessions_expires_at"),
        table_name="auth_refresh_sessions",
    )
    op.drop_table("auth_refresh_sessions")

    op.drop_index(
        op.f("ix_user_route_permissions_user_id"),
        table_name="user_route_permissions",
    )
    op.drop_index(
        op.f("ix_user_route_permissions_route_path"),
        table_name="user_route_permissions",
    )
    op.drop_table("user_route_permissions")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_is_active"), table_name="users")
    op.drop_table("users")
