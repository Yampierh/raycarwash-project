"""
domains/vehicles/vehicle_photo.py — VehiclePhoto model.

Multiple photos per vehicle (max 4 enforced at the service layer in
Phase 4 chunk V). Photos live in the public S3 bucket (Phase 0 chunk C
`BUCKET_PUBLIC`) behind the FileStorageAdapter contract. The Profile
Hub's `vehicles[]` block exposes the FIRST photo (by sort_order) as
`photo_url`; the dedicated VehiclePhotos screen lists all of them.

Migration: m_009.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base


class VehiclePhoto(Base):
    __tablename__ = "vehicle_photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(String(255), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="photos")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<VehiclePhoto id={self.id} vehicle_id={self.vehicle_id} order={self.sort_order}>"


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from domains.vehicles.models import Vehicle  # noqa: F401
