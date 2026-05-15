"""m_001c extend audit_log: old_value, new_value, ip_address, user_agent, request_id

Adds forensics fields used by the AuditContextMiddleware. Renames
`stripe_metadata` → `metadata_` to make it generic (Profile audit entries use
the same column for cross-domain metadata).

Per ADR-006, `old_value`/`new_value` are full JSONB for 0-90 days, then
redacted by `workers/audit_log_redactor.py`.

Revision ID: m_001c
Revises: m_001b
Create Date: 2026-05-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_001c"
down_revision = "m_001b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New forensic / changeset columns
    op.add_column(
        "audit_logs",
        sa.Column("old_value", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("new_value", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("user_agent", sa.Text, nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("request_id", sa.String(64), nullable=True),
    )

    # Rename stripe_metadata → metadata_
    op.alter_column("audit_logs", "stripe_metadata", new_column_name="metadata_")


def downgrade() -> None:
    op.alter_column("audit_logs", "metadata_", new_column_name="stripe_metadata")
    op.drop_column("audit_logs", "request_id")
    op.drop_column("audit_logs", "user_agent")
    op.drop_column("audit_logs", "ip_address")
    op.drop_column("audit_logs", "new_value")
    op.drop_column("audit_logs", "old_value")
