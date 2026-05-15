"""m_004 provider_profile public fields

Adds the fields the Profile Hub `provider` block exposes and the public
provider profile endpoint will consume in Phase 7:

  display_name          — public display name distinct from legal_full_name
  business_name         — LLC / DBA
  tagline               — short pitch (140 chars)
  social_links          — JSONB {instagram, tiktok, website}
  insurance_policy_number_encrypted  — EncryptedType in the model
  tax_id_encrypted                   — EncryptedType in the model
  payout_method_id      — Stripe Connect account ID (Phase 5+)
  cover_photo_s3_key    — header image
  total_services_completed  — denormalized counter for stats block
  earnings_lifetime_cents   — denormalized sum (BIGINT)

Revision ID: m_004
Revises: m_003
Create Date: 2026-05-14
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_004"
down_revision = "m_003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("provider_profiles", sa.Column("display_name", sa.String(80), nullable=True))
    op.add_column("provider_profiles", sa.Column("business_name", sa.String(120), nullable=True))
    op.add_column("provider_profiles", sa.Column("tagline", sa.String(140), nullable=True))
    op.add_column(
        "provider_profiles",
        sa.Column("social_links", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # EncryptedType serializes as String at the SQL level — column type matches.
    op.add_column(
        "provider_profiles",
        sa.Column("insurance_policy_number_encrypted", sa.String(255), nullable=True),
    )
    op.add_column(
        "provider_profiles",
        sa.Column("tax_id_encrypted", sa.String(255), nullable=True),
    )

    op.add_column("provider_profiles", sa.Column("payout_method_id", sa.String(64), nullable=True))
    op.add_column("provider_profiles", sa.Column("cover_photo_s3_key", sa.String(255), nullable=True))

    op.add_column(
        "provider_profiles",
        sa.Column(
            "total_services_completed", sa.Integer(),
            nullable=False, server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "provider_profiles",
        sa.Column(
            "earnings_lifetime_cents", sa.BigInteger(),
            nullable=False, server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("provider_profiles", "earnings_lifetime_cents")
    op.drop_column("provider_profiles", "total_services_completed")
    op.drop_column("provider_profiles", "cover_photo_s3_key")
    op.drop_column("provider_profiles", "payout_method_id")
    op.drop_column("provider_profiles", "tax_id_encrypted")
    op.drop_column("provider_profiles", "insurance_policy_number_encrypted")
    op.drop_column("provider_profiles", "social_links")
    op.drop_column("provider_profiles", "tagline")
    op.drop_column("provider_profiles", "business_name")
    op.drop_column("provider_profiles", "display_name")
