from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Numeric,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
        Index("ix_appointments_client_scheduled", "client_id", "scheduled_time", "is_deleted"),
        Index("ix_appointments_detailer_status_scheduled", "detailer_id", "status", "scheduled_time"),
        CheckConstraint("estimated_price >= 0", name="ck_appointments_estimated_price_nonnegative"),
        CheckConstraint("actual_price IS NULL OR actual_price >= 0", name="ck_appointments_actual_price_nonnegative"),
        CheckConstraint("service_latitude IS NULL OR (service_latitude >= -90 AND service_latitude <= 90)", name="ck_appointments_service_latitude_range"),
        CheckConstraint("service_longitude IS NULL OR (service_longitude >= -180 AND service_longitude <= 180)", name="ck_appointments_service_longitude_range"),
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

    # ── Price-ﬁeld aliases (Plan 24 convention: DB column is `estimated_price`
    # without _cents for legacy compat, but Python code prefers the _cents
    # suﬃx used everywhere else – models, schemas, FareEstimate, etc.).
    @property
    def estimated_price_cents(self) -> int:
        return self.estimated_price

    @property
    def actual_price_cents(self) -> int | None:
        return self.actual_price

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} status={self.status} scheduled={self.scheduled_time.isoformat()}>"


class AppointmentVehicle(Base):
    __tablename__ = "appointment_vehicles"
    __table_args__ = (
        UniqueConstraint("appointment_id", "vehicle_id", name="uq_appointment_vehicle_pair"),
        CheckConstraint("price_cents >= 0", name="ck_appointment_vehicles_price_nonnegative"),
        CheckConstraint("duration_minutes > 0", name="ck_appointment_vehicles_duration_positive"),
    )

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
    __table_args__ = (
        UniqueConstraint("appointment_id", "addon_id", name="uq_appointment_addon_pair"),
        CheckConstraint("price_cents >= 0", name="ck_appointment_addons_price_nonnegative"),
        CheckConstraint("duration_minutes > 0", name="ck_appointment_addons_duration_positive"),
    )

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
    __table_args__ = (
        UniqueConstraint("appointment_id", "detailer_id", name="uq_assignment_appointment_detailer"),
        Index("ix_assignment_status_expires", "status", "offer_expires_at"),
    )

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


class AppointmentStatusHistory(Base):
    """Immutable-ish operational history of appointment status changes."""
    __tablename__ = "appointment_status_history"
    __table_args__ = (
        Index("ix_appointment_status_history_appointment_created", "appointment_id", "created_at"),
        Index("ix_appointment_status_history_actor_created", "actor_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    old_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class AppointmentCancellation(Base):
    """Cancellation snapshot for refunds, support, and dispute handling."""
    __tablename__ = "appointment_cancellations"
    __table_args__ = (
        UniqueConstraint("appointment_id", name="uq_appointment_cancellations_appointment"),
        Index("ix_appointment_cancellations_cancelled_by", "cancelled_by_user_id", "created_at"),
        CheckConstraint("refund_amount_cents IS NULL OR refund_amount_cents >= 0", name="ck_appointment_cancellations_refund_amount_nonnegative"),
        CheckConstraint("refund_percent IS NULL OR (refund_percent >= 0 AND refund_percent <= 100)", name="ck_appointment_cancellations_refund_percent_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=False,
    )
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    cancelled_by_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    refund_amount_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    refund_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    policy_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.users.models import User
    from domains.vehicles.models import Vehicle
    from domains.services_catalog.models import Service, Addon
    from domains.reviews.models import Review
