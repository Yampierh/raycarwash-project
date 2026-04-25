from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class ProviderProfile(TimestampMixin, Base):
    __tablename__ = "provider_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    years_of_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_accepting_bookings: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    service_radius_miles: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    working_hours: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        default=lambda: {
            "monday":    {"start": "08:00", "end": "18:00", "enabled": True},
            "tuesday":   {"start": "08:00", "end": "18:00", "enabled": True},
            "wednesday": {"start": "08:00", "end": "18:00", "enabled": True},
            "thursday":  {"start": "08:00", "end": "18:00", "enabled": True},
            "friday":    {"start": "08:00", "end": "18:00", "enabled": True},
            "saturday":  {"start": "09:00", "end": "16:00", "enabled": True},
            "sunday":    {"start": None,     "end": None,    "enabled": False},
        },
    )
    timezone: Mapped[str] = mapped_column(
        String(60), nullable=False, default="America/Indiana/Indianapolis",
    )
    service_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("service_categories.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    average_rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    total_reviews: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    specialties_rel: Mapped[list[Specialty]] = relationship(
        "Specialty", secondary="provider_specialties",
        back_populates="providers", lazy="selectin",
    )

    @property
    def specialties(self) -> list[str]:
        return [s.slug for s in (self.specialties_rel or [])]

    # Location
    current_lat: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    current_lng: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    last_location_update: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Stripe Identity verification
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_submitted")
    legal_full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stripe_verification_session_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
    )
    background_check_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    background_check_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # H3 geospatial index
    h3_index_r7: Mapped[str | None] = mapped_column(String(20), nullable=True)
    h3_index_r9: Mapped[str | None] = mapped_column(String(20), nullable=True)
    response_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False, default=Decimal("0"), server_default="0",
    )

    user: Mapped[User] = relationship("User", back_populates="provider_profile")
    detailer_services: Mapped[list[DetailerService]] = relationship(
        "DetailerService", back_populates="detailer",
        lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ProviderProfile user_id={self.user_id}>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.users.models import User
    from domains.services_catalog.models import Specialty, DetailerService
