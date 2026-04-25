from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text,
    UniqueConstraint, text as sa_text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class ServiceCategory(str, enum.Enum):
    BASIC_WASH       = "basic_wash"
    INTERIOR_DETAIL  = "interior_detail"
    FULL_DETAIL      = "full_detail"
    CERAMIC_COATING  = "ceramic_coating"
    PAINT_CORRECTION = "paint_correction"


class ServiceCategoryTable(TimestampMixin, Base):
    __tablename__ = "service_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    def __repr__(self) -> str:
        return f"<ServiceCategory {self.slug}>"


class Service(TimestampMixin, Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ServiceCategory] = mapped_column(
        Enum(ServiceCategory, name="service_category_enum"), nullable=False,
    )
    base_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    base_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    price_small: Mapped[int] = mapped_column(Integer, nullable=False)
    price_medium: Mapped[int] = mapped_column(Integer, nullable=False)
    price_large: Mapped[int] = mapped_column(Integer, nullable=False)
    price_xl: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_small_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_medium_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_large_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_xl_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", back_populates="service", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Service id={self.id} name={self.name!r}>"


class Addon(TimestampMixin, Base):
    __tablename__ = "addons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Addon id={self.id} name={self.name!r} price={self.price_cents}¢>"


class DetailerService(TimestampMixin, Base):
    __tablename__ = "detailer_services"
    __table_args__ = (UniqueConstraint("detailer_id", "service_id", name="uq_detailer_service"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    detailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    custom_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    detailer: Mapped[ProviderProfile] = relationship("ProviderProfile", back_populates="detailer_services")
    service: Mapped[Service] = relationship("Service")

    def __repr__(self) -> str:
        return f"<DetailerService detailer={self.detailer_id} service={self.service_id}>"


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    providers: Mapped[list[ProviderProfile]] = relationship(
        "ProviderProfile", secondary="provider_specialties", back_populates="specialties_rel",
    )

    def __repr__(self) -> str:
        return f"<Specialty slug={self.slug!r}>"


class ProviderSpecialty(Base):
    __tablename__ = "provider_specialties"

    provider_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id", ondelete="CASCADE"), primary_key=True,
    )
    specialty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("specialties.id", ondelete="CASCADE"), primary_key=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa_text("now()"),
    )

    def __repr__(self) -> str:
        return f"<ProviderSpecialty profile={self.provider_profile_id} specialty={self.specialty_id}>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.appointments.models import Appointment
    from domains.providers.models import ProviderProfile
