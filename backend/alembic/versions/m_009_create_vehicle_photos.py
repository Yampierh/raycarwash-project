"""m_009 create vehicle_photos

Multiple photos per vehicle (max 4 enforced at the service layer).
Photos live in the public S3 bucket (Phase 0 chunk C `BUCKET_PUBLIC`)
behind the FileStorageAdapter contract. The Hub's `vehicles[]` block
exposes the FIRST photo as `photo_url`; the dedicated VehiclePhotos
screen lists all of them.

Revision ID: m_009
Revises: m_008
Create Date: 2026-05-15
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_009"
down_revision = "m_008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("s3_key", sa.String(255), nullable=False),
        sa.Column("caption", sa.String(120), nullable=True),
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

    # Per-vehicle listing, ordered for the gallery.
    op.create_index(
        "idx_vehicle_photos_vehicle_order",
        "vehicle_photos",
        ["vehicle_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("idx_vehicle_photos_vehicle_order", table_name="vehicle_photos")
    op.drop_table("vehicle_photos")
