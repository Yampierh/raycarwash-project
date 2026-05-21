from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class Review(TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("appointment_id", name="uq_review_appointment"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
        CheckConstraint(
            "moderation_state IN ('auto_pending', 'approved', 'hidden')",
            name="ck_reviews_moderation_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    detailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True,
        comment="Denormalised for fast detailer rating queries.",
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # W2-D moderation columns — see m_026 docstring for the state machine.
    moderation_state: Mapped[str] = mapped_column(
        String(16), nullable=False,
        default="auto_pending", server_default="auto_pending",
    )
    moderation_actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    moderation_acted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    moderation_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    appointment: Mapped[Appointment] = relationship("Appointment", back_populates="review")
    reviewer: Mapped[User] = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")

    def __repr__(self) -> str:
        return f"<Review id={self.id} rating={self.rating} appointment={self.appointment_id}>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.appointments.models import Appointment
    from domains.users.models import User
