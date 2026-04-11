"""add detailer verification fields

Revision ID: 860f2d1f8752
Revises:
Create Date: 2026-04-10

Adds identity-verification columns to detailer_profiles:
  - verification_status       (varchar 20, default 'not_submitted')
  - legal_full_name           (varchar 200)
  - date_of_birth             (date)
  - address_line1             (varchar 200)
  - city                      (varchar 120)
  - state                     (varchar 60)
  - zip_code                  (varchar 20)
  - stripe_verification_session_id (varchar 100, indexed)
  - background_check_consent  (bool, default false)
  - background_check_consent_at (timestamptz)
  - verification_submitted_at (timestamptz)
  - verification_reviewed_at  (timestamptz)
  - rejection_reason          (text)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision = "860f2d1f8752"
down_revision = None   # set to the last migration ID if one exists
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "detailer_profiles",
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="not_submitted",
            comment="not_submitted | pending | approved | rejected",
        ),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column("legal_full_name", sa.String(200), nullable=True),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column("date_of_birth", sa.Date(), nullable=True),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column("address_line1", sa.String(200), nullable=True),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column("city", sa.String(120), nullable=True),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column("state", sa.String(60), nullable=True),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column("zip_code", sa.String(20), nullable=True),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column(
            "stripe_verification_session_id",
            sa.String(100),
            nullable=True,
            comment="Stripe Identity VerificationSession ID (vs_xxx).",
        ),
    )
    op.create_index(
        "ix_detailer_profiles_stripe_verification_session_id",
        "detailer_profiles",
        ["stripe_verification_session_id"],
    )
    op.add_column(
        "detailer_profiles",
        sa.Column(
            "background_check_consent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column(
            "background_check_consent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column(
            "verification_submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column(
            "verification_reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "detailer_profiles",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_detailer_profiles_stripe_verification_session_id",
        table_name="detailer_profiles",
    )
    for col in [
        "rejection_reason",
        "verification_reviewed_at",
        "verification_submitted_at",
        "background_check_consent_at",
        "background_check_consent",
        "stripe_verification_session_id",
        "zip_code",
        "state",
        "city",
        "address_line1",
        "date_of_birth",
        "legal_full_name",
        "verification_status",
    ]:
        op.drop_column("detailer_profiles", col)
