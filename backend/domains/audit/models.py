from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base


class AuditAction(str, enum.Enum):
    # Appointment lifecycle
    APPOINTMENT_CREATED        = "appointment_created"
    APPOINTMENT_STATUS_CHANGED = "appointment_status_changed"
    APPOINTMENT_DELETED        = "appointment_deleted"
    # Payment events
    PAYMENT_INTENT_CREATED = "payment_intent_created"
    PAYMENT_CAPTURED       = "payment_captured"
    PAYMENT_REFUNDED       = "payment_refunded"
    # Auth events
    USER_REGISTERED          = "user_registered"
    USER_LOGIN               = "user_login"
    USER_SOCIAL_LOGIN        = "user_social_login"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    # Review events
    REVIEW_CREATED = "review_created"
    # Detailer profile events
    DETAILER_PROFILE_CREATED = "provider_profile_created"
    DETAILER_PROFILE_UPDATED = "provider_profile_updated"


class AuditLog(Base):
    """Append-only audit trail. No TimestampMixin — immutable by design."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_actor_action", "actor_id", "action",
              postgresql_where="actor_id IS NOT NULL"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    action: Mapped[AuditAction] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    stripe_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    actor: Mapped[User | None] = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} entity={self.entity_type}:{self.entity_id}>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.users.models import User
