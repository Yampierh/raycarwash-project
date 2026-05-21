"""
domains/users/user_address.py — UserAddress model.

Backs the `addresses` block of the Profile Hub (ADR-002b) and supersedes
the legacy `ClientProfile.service_address` single string.

Phase 4 stores plain text for line1/city/state/zip — labels and notes
included — because the matching engine + booking flow need them readable
without per-row decryption. Wrap with EncryptedType later if PII review
demands it.

Geocoded denormalization (latitude/longitude/h3_index_r9) comes from the
GeocodingAdapter (Nominatim in dev, Google Maps in prod). The H3 r9 index
is the matching engine's lookup key.

Migrations: m_006 (table + indices) + m_010 (FK from
client_profiles.default_address_id → user_addresses.id).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy import Numeric, text as sa_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class UserAddress(TimestampMixin, Base):
    __tablename__ = "user_addresses"
    __table_args__ = (
        Index("idx_user_addresses_user_active", "user_id", sa_text("created_at DESC"), postgresql_where=sa_text("is_deleted = false")),
        Index("idx_user_addresses_h3", "h3_index_r9", postgresql_where=sa_text("h3_index_r9 IS NOT NULL AND is_deleted = false")),
        Index("idx_user_addresses_default_unique", "user_id", unique=True, postgresql_where=sa_text("is_default = true AND is_deleted = false")),
        CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_user_addresses_latitude_range"),
        CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="ck_user_addresses_longitude_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    line1: Mapped[str] = mapped_column(String(200), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(60), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(
        String(60), nullable=False, default="US", server_default="US",
    )

    # Numeric(9,6) → ~10 cm precision, plenty for matching radius.
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    h3_index_r9: Mapped[str | None] = mapped_column(String(20), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="addresses")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<UserAddress id={self.id} user_id={self.user_id} label={self.label!r}>"


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from domains.users.models import User  # noqa: F401
