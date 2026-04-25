from __future__ import annotations

import enum
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class VehicleSize(str, enum.Enum):
    SMALL  = "small"
    MEDIUM = "medium"
    LARGE  = "large"
    XL     = "xl"


class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        UniqueConstraint("owner_id", "license_plate", name="uq_vehicle_owner_plate"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )

    vin: Mapped[str | None] = mapped_column(String(17), index=True, nullable=True)
    make: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str] = mapped_column(String(60), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    series: Mapped[str | None] = mapped_column(String(60), nullable=True)
    color: Mapped[str] = mapped_column(String(40), nullable=False)
    license_plate: Mapped[str] = mapped_column(String(20), nullable=False)
    body_class: Mapped[str | None] = mapped_column(String(60), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[User] = relationship("User", back_populates="vehicles")
    appointments: Mapped[list[Appointment]] = relationship(
        "Appointment", back_populates="vehicle", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Vehicle {self.year} {self.make} {self.model} ({self.license_plate})>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.users.models import User
    from domains.appointments.models import Appointment
