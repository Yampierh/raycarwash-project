from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
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
    REVIEW_MODERATED = "review_moderated"  # Plan 24 W2-D: admin approve/hide
    # Customer credit events (Plan 24 W2-E)
    CUSTOMER_CREDIT_ISSUED = "customer_credit_issued"
    CUSTOMER_CREDIT_REVOKED = "customer_credit_revoked"
    # Detailer profile events
    DETAILER_PROFILE_CREATED = "provider_profile_created"
    DETAILER_PROFILE_UPDATED = "provider_profile_updated"
    # Profile system (ADR-001)
    PROFILE_UPDATED            = "profile_updated"
    AVATAR_CHANGED             = "avatar_changed"
    COVER_CHANGED              = "cover_changed"
    EMAIL_CHANGE_REQUESTED     = "email_change_requested"
    EMAIL_CHANGED             = "email_changed"
    PHONE_CHANGE_REQUESTED    = "phone_change_requested"
    PHONE_CHANGED             = "phone_changed"
    PASSWORD_CHANGED           = "password_changed"
    TWO_FA_ENABLED            = "two_fa_enabled"
    TWO_FA_DISABLED           = "two_fa_disabled"
    PASSKEY_REGISTERED        = "passkey_registered"
    PASSKEY_REVOKED           = "passkey_revoked"
    SESSION_REVOKED           = "session_revoked"
    ALL_SESSIONS_REVOKED      = "all_sessions_revoked"
    PAYMENT_METHOD_ADDED      = "payment_method_added"
    PAYMENT_METHOD_REMOVED    = "payment_method_removed"
    PAYMENT_METHOD_DEFAULT    = "payment_method_default"
    ADDRESS_ADDED             = "address_added"
    ADDRESS_UPDATED           = "address_updated"
    ADDRESS_REMOVED           = "address_removed"
    VEHICLE_ADDED             = "vehicle_added"
    VEHICLE_UPDATED           = "vehicle_updated"
    VEHICLE_REMOVED           = "vehicle_removed"
    FAVORITE_ADDED            = "favorite_added"
    FAVORITE_REMOVED          = "favorite_removed"
    DOCUMENT_UPLOADED         = "document_uploaded"
    DOCUMENT_DELETED          = "document_deleted"
    PROVIDER_MODE_SWITCHED    = "provider_mode_switched"
    PROVIDER_PROFILE_UPDATED   = "provider_profile_updated"
    PROVIDER_STATUS_CHANGED    = "provider_status_changed"
    ROLE_SWITCHED              = "role_switched"
    NOTIFICATION_PREFS_UPDATED = "notification_prefs_updated"
    PRIVACY_SETTINGS_UPDATED   = "privacy_settings_updated"
    DATA_EXPORT_REQUESTED     = "data_export_requested"
    DATA_EXPORT_READY         = "data_export_ready"
    ACCOUNT_DELETION_REQUESTED = "account_deletion_requested"
    ACCOUNT_DELETION_CANCELLED = "account_deletion_cancelled"
    ACCOUNT_ANONYMIZED        = "account_anonymized"


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
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata_", JSONB, nullable=True)
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
