from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin
from domains.vehicles.models import VehicleSize


class AppointmentStatus(str, enum.Enum):
    PENDING               = "pending"
    CONFIRMED             = "confirmed"
    ARRIVED               = "arrived"
    IN_PROGRESS           = "in_progress"
    COMPLETED             = "completed"
    CANCELLED_BY_CLIENT   = "cancelled_by_client"
    CANCELLED_BY_DETAILER = "cancelled_by_detailer"
    NO_SHOW               = "no_show"
    SEARCHING             = "searching"
    NO_DETAILER_FOUND     = "no_detailer_found"


class AssignmentStatus(str, enum.Enum):
    OFFERED  = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TIMEOUT  = "timeout"


TERMINAL_STATUSES: frozenset[AppointmentStatus] = frozenset({
    AppointmentStatus.CANCELLED_BY_CLIENT,
    AppointmentStatus.CANCELLED_BY_DETAILER,
    AppointmentStatus.NO_SHOW,
    AppointmentStatus.NO_DETAILER_FOUND,
})

VALID_TRANSITIONS: dict[AppointmentStatus, dict[AppointmentStatus, frozenset[str]]] = {
    AppointmentStatus.PENDING: {
        AppointmentStatus.CONFIRMED:             frozenset({"detailer", "admin"}),
        AppointmentStatus.CANCELLED_BY_CLIENT:   frozenset({"client",   "admin"}),
        AppointmentStatus.CANCELLED_BY_DETAILER: frozenset({"detailer", "admin"}),
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.ARRIVED:               frozenset({"detailer", "admin"}),
        AppointmentStatus.IN_PROGRESS:           frozenset({"detailer", "admin"}),
        AppointmentStatus.CANCELLED_BY_CLIENT:   frozenset({"client",   "admin"}),
        AppointmentStatus.CANCELLED_BY_DETAILER: frozenset({"detailer", "admin"}),
    },
    AppointmentStatus.ARRIVED: {
        AppointmentStatus.IN_PROGRESS:           frozenset({"detailer", "admin"}),
        AppointmentStatus.CANCELLED_BY_CLIENT:   frozenset({"client",   "admin"}),
        AppointmentStatus.CANCELLED_BY_DETAILER: frozenset({"detailer", "admin"}),
    },
    AppointmentStatus.IN_PROGRESS: {
        AppointmentStatus.COMPLETED: frozenset({"detailer", "admin"}),
        AppointmentStatus.NO_SHOW:   frozenset({"detailer", "admin"}),
    },
    AppointmentStatus.COMPLETED:              {},
    AppointmentStatus.CANCELLED_BY_CLIENT:    {},
    AppointmentStatus.CANCELLED_BY_DETAILER:  {},
    AppointmentStatus.NO_SHOW:                {},
}


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_detailer_scheduled", "detailer_id", "scheduled_time", "is_deleted"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    detailer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True, index=True,
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False,
    )

    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    estimated_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    travel_buffer_end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)

    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status_enum"),
        nullable=False, default=AppointmentStatus.PENDING, index=True,
    )

    estimated_price: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_price: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    client_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    detailer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_latitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)
    service_longitude: Mapped[float | None] = mapped_column(Numeric(9, 6), nullable=True)

    client: Mapped[User] = relationship(
        "User", foreign_keys=[client_id], back_populates="client_appointments", lazy="selectin",
    )
    detailer: Mapped[User] = relationship(
        "User", foreign_keys=[detailer_id], back_populates="detailer_appointments", lazy="selectin",
    )
    vehicle: Mapped[Vehicle] = relationship("Vehicle", back_populates="appointments", lazy="selectin")
    service: Mapped[Service] = relationship("Service", back_populates="appointments", lazy="selectin")
    review: Mapped[Review | None] = relationship(
        "Review", back_populates="appointment", uselist=False, lazy="selectin",
    )
    appointment_vehicles: Mapped[list[AppointmentVehicle]] = relationship(
        "AppointmentVehicle", back_populates="appointment",
        lazy="selectin", cascade="all, delete-orphan",
    )
    appointment_addons: Mapped[list[AppointmentAddon]] = relationship(
        "AppointmentAddon", back_populates="appointment",
        lazy="selectin", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} status={self.status} scheduled={self.scheduled_time.isoformat()}>"


class AppointmentVehicle(Base):
    __tablename__ = "appointment_vehicles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False,
    )
    vehicle_size: Mapped[VehicleSize] = mapped_column(
        Enum(VehicleSize, name="vehicle_size_enum", create_type=False), nullable=False,
    )
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    appointment: Mapped[Appointment] = relationship("Appointment", back_populates="appointment_vehicles")
    vehicle: Mapped[Vehicle] = relationship("Vehicle", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AppointmentVehicle appt={self.appointment_id} vehicle={self.vehicle_id}>"


class AppointmentAddon(Base):
    __tablename__ = "appointment_addons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    addon_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("addons.id", ondelete="RESTRICT"), nullable=False,
    )
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    appointment: Mapped[Appointment] = relationship("Appointment", back_populates="appointment_addons")
    addon: Mapped[Addon] = relationship("Addon")

    def __repr__(self) -> str:
        return f"<AppointmentAddon appt={self.appointment_id} addon={self.addon_id}>"


class AppointmentAssignment(Base):
    __tablename__ = "appointment_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    detailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    offered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AssignmentStatus.OFFERED.value)
    offer_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<AppointmentAssignment appt={self.appointment_id} detailer={self.detailer_id}>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.users.models import User
    from domains.vehicles.models import Vehicle
    from domains.services_catalog.models import Service, Addon
    from domains.reviews.models import Review
