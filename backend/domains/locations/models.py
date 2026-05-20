"""
domains/locations/models.py — Geographic reference tables (Plan 24).

The `cities` table is the canonical list of markets RayCarWash operates
in. Other tables (`provider_profiles.home_city_code`, future
`service_zones`, future `surge_rules`) reference cities by their
short `code` (e.g. `fwa`, `ind`).

Why `code` is the natural FK key (vs UUID):
  - URLs and admin filters (`?city=fwa`) read more cleanly.
  - Cross-system reporting (Stripe, Twilio) often uses 3-4 letter
    codes for market labels — easier to align.
  - The set is small (~10) and stable; UUID is overkill.

Soft-delete via TimestampMixin so cities can be retired without
breaking historical references.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TimestampMixin


class CityStatus(str, enum.Enum):
    PLANNED = "planned"   # on the roadmap, not yet live
    PILOT   = "pilot"     # limited launch, ops watching closely
    ACTIVE  = "active"    # general availability
    PAUSED  = "paused"    # temporarily not accepting new bookings


class City(TimestampMixin, Base):
    """A market RayCarWash operates in (or plans to)."""

    __tablename__ = "cities"
    __table_args__ = (
        UniqueConstraint("code", name="uq_cities_code"),
        Index("ix_cities_status_sort", "status", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    # 3-4 letter market code. Stable, URL-safe, used as FK target.
    code: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    # IANA timezone string (e.g. "America/Indiana/Indianapolis").
    # Used to interpret detailer working_hours + customer scheduled_time.
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=CityStatus.PILOT.value,
        server_default=CityStatus.PILOT.value,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )

    def __repr__(self) -> str:
        return f"<City code={self.code} name={self.name} status={self.status}>"
