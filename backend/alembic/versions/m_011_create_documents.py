"""m_011 create documents

Backs the `/users/me/provider-documents/*` endpoints (Phase 5).
Stores KYC artifacts (insurance, business license, certifications,
W-9) for detailers. Files themselves land in the private S3 bucket
(`raycarwash-private-docs` per ADR-008) — only the s3_key + metadata
lives here.

`type` is a String (no PG ENUM) for forward-compat with future doc
categories. `expires_at` powers the `workers/document_expiry_checker.py`
cron that nudges detailers 30 days before their insurance lapses.

Revision ID: m_011
Revises: m_010
Create Date: 2026-05-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_011"
down_revision = "m_010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # "insurance" | "business_license" | "certification" | "w9" | "other"
        sa.Column("type", sa.String(40), nullable=False),
        sa.Column("title", sa.String(120), nullable=True),
        sa.Column("s3_key", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(80), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        # ISO date — when the document loses validity. Insurance certs
        # are the primary driver; other types may leave it NULL.
        sa.Column("expires_at", sa.Date, nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Per-user listing, filtered by type, newest first.
    op.create_index(
        "idx_documents_user_type",
        "documents",
        ["user_id", "type", sa.text("created_at DESC")],
        postgresql_where=sa.text("is_deleted = false"),
    )

    # Worker scans for expirations within the next ~30 days. The partial
    # index keeps the scan cheap (most rows have expires_at = NULL).
    op.create_index(
        "idx_documents_expiring",
        "documents",
        ["expires_at"],
        postgresql_where=sa.text(
            "expires_at IS NOT NULL AND is_deleted = false"
        ),
    )


def downgrade() -> None:
    op.drop_index("idx_documents_expiring", table_name="documents")
    op.drop_index("idx_documents_user_type", table_name="documents")
    op.drop_table("documents")
