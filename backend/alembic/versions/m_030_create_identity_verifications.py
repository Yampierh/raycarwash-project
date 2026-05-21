"""m_030 create identity_verifications table for KYC/identity verification

Creates the persisted KYC state for provider identity verification.
Each provider user gets exactly one row (unique user_id).  The row is
created on first document submission and updated on subsequent resubmits
or admin review outcomes.

Revision ID: m_030
Revises: m_029
Create Date: 2026-05-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_030"
down_revision = "m_029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False, unique=True, index=True,
        ),
        sa.Column("status", sa.String(30), nullable=False,
                  server_default="PENDING"),
        sa.Column("verification_provider", sa.String(50), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True, index=True),
        sa.Column("document_data", postgresql.JSONB, nullable=False,
                  server_default="{}"),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean, nullable=False,
                  server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("identity_verifications")
