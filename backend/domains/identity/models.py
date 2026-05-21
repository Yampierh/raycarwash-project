from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class KycStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class IdentityVerification(TimestampMixin, Base):
    __tablename__ = "identity_verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=KycStatus.PENDING.value,
    )
    verification_provider: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True,
    )
    document_data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    user: Mapped[User] = relationship("User", lazy="select")

    def __repr__(self) -> str:
        return f"<IdentityVerification user={self.user_id} status={self.status}>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.users.models import User
