from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class OnboardingState(TimestampMixin, Base):
    __tablename__ = "onboarding_states"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending_registration",
    )
    current_step: Mapped[str | None] = mapped_column(String(50), nullable=True)
    state_data: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict,
    )
    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )

    user: Mapped[User] = relationship("User", lazy="select")

    def __repr__(self) -> str:
        return f"<OnboardingState user={self.user_id} status={self.status}>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.users.models import User
