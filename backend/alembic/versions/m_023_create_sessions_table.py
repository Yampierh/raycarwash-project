"""m_023 create sessions table for stateful auth control

Plan 23 (Fase 1) — sessions backed by Redis cache + DB for real-time
session revocation, device tracking, and anomaly detection.

Designed per CR feedback:
  - family_id is NOT unique (it's a rotation chain, not a session id)
  - NO FK to refresh_tokens.family_id (app-level integrity)
  - Indexes only in Alembic, NOT in ORM __table_args__ (avoids drift)
  - last_active_at uses server_default only (no dual Python/DB source of truth)

Revision ID: m_023
Revises: m_020
Create Date: 2026-05-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_023"
down_revision = "m_020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_name", sa.String(120), nullable=True),
        sa.Column("device_type", sa.String(20), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("ip_country", sa.String(4), nullable=True),
        sa.Column("ip_city", sa.String(100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index(
        "ix_sessions_user_active",
        "sessions",
        ["user_id"],
        postgresql_where=sa.text("revoked = FALSE"),
    )
    op.create_index(
        "ix_sessions_user_last_active",
        "sessions",
        ["user_id"],
        postgresql_include=["last_active_at"],
    )
    op.create_index("ix_sessions_family_id", "sessions", ["family_id"])


def downgrade() -> None:
    op.drop_table("sessions")
