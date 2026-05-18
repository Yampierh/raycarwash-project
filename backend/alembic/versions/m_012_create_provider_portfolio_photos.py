"""m_012 create provider_portfolio_photos

Detailer portfolio gallery (max 30 per provider, enforced at the
service layer). Photos live in the public S3 bucket — they're shown
on the public provider profile so non-authenticated clients can
preview work. `tag` is a free-form String with "before"/"after"/"hero"
as the conventional values; we don't enum-constrain so detailers can
add their own grouping ("ceramic_coating", "interior", etc.) without
a schema migration.

Revision ID: m_012
Revises: m_011
Create Date: 2026-05-18
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_012"
down_revision = "m_011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_portfolio_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("s3_key", sa.String(255), nullable=False),
        sa.Column("caption", sa.String(200), nullable=True),
        sa.Column("tag", sa.String(40), nullable=True),
        sa.Column(
            "sort_order",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Gallery listing for the public provider page.
    op.create_index(
        "idx_portfolio_provider_order",
        "provider_portfolio_photos",
        ["provider_user_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_portfolio_provider_order",
        table_name="provider_portfolio_photos",
    )
    op.drop_table("provider_portfolio_photos")
