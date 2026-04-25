"""add missing performance indexes

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-25

Adds three indexes that were identified as missing during the architectural audit:

1. ix_audit_logs_actor_action  — composite (actor_id, action) on audit_logs
   Speeds up: "show all login events for user X"
   Query:  WHERE actor_id = :uid AND action = 'user_login'
   Without this, Postgres uses the single-column ix_audit_logs_actor_id index
   and then filters action in memory — acceptable now, slow at >1M audit rows.

2. ix_refresh_tokens_expires_at — (expires_at) on refresh_tokens
   Required by the cleanup job that prunes expired tokens.
   Without this, the cleanup UPDATE scans the entire table.

3. ix_user_roles_role_id — (role_id) on user_roles
   Speeds up: "all users assigned role Y" (admin dashboard / permission checks).
   The existing primary key (user_id, role_id) does not help for role_id-only
   lookups in PostgreSQL — it only covers leading-column (user_id) queries.
"""
from __future__ import annotations

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # audit_logs: composite index for (actor_id, action) lookups
    op.create_index(
        "ix_audit_logs_actor_action",
        "audit_logs",
        ["actor_id", "action"],
        postgresql_where="actor_id IS NOT NULL",  # partial: skip system events
    )

    # refresh_tokens: index for cleanup jobs (DELETE/UPDATE WHERE expires_at < NOW())
    op.create_index(
        "ix_refresh_tokens_expires_at",
        "refresh_tokens",
        ["expires_at"],
    )

    # user_roles: index for role_id-only queries ("all users with role X")
    op.create_index(
        "ix_user_roles_role_id",
        "user_roles",
        ["role_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_roles_role_id",          table_name="user_roles")
    op.drop_index("ix_refresh_tokens_expires_at",   table_name="refresh_tokens")
    op.drop_index("ix_audit_logs_actor_action",     table_name="audit_logs")
