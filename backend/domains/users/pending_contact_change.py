"""
domains/users/pending_contact_change.py — PendingContactChange model.

The new email or phone value is held in an encrypted row until the user
proves they control the destination (link click / OTP). Until then,
`users.email` and `users.phone_number` remain untouched, so a stolen
session cannot pivot to a new contact without re-authentication AND
proof of receipt at the new address.

See plan §6.4 + ADR-001 (anti-takeover).
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import EncryptedType

from infrastructure.db.base import Base, _get_encryption_key


class ContactChangeType(str, enum.Enum):
    EMAIL = "email"
    PHONE = "phone"


class PendingContactChange(Base):
    __tablename__ = "pending_contact_changes"
    __table_args__ = (
        Index("idx_pending_contact_token", "verification_token_hash"),
        Index("idx_pending_contact_expires", "expires_at"),
        Index("idx_pending_contact_user_type", "user_id", "change_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # ContactChangeType enum stored as String (no PG ENUM type — keeps the
    # migration story simple and matches AuditAction's approach).
    change_type: Mapped[str] = mapped_column(String(10), nullable=False)

    # PII at rest. EncryptedType uses the same Fernet key as User.full_name.
    new_value_encrypted: Mapped[str] = mapped_column(
        EncryptedType(String(255), _get_encryption_key), nullable=False,
    )
    # Deterministic HMAC of the new value — lets us check "is this email
    # already pending for someone else?" without decrypting.
    new_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # One-way hash of the token mailed (64-char random) or the OTP digits.
    verification_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # OTP attempt counter. Email tokens are single-use so this stays at 0
    # for them; phone OTP locks at 5.
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="pending_contact_changes")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<PendingContactChange user_id={self.user_id} type={self.change_type}>"


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from domains.users.models import User  # noqa: F401
