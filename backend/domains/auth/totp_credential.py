"""
domains/auth/totp_credential.py — TotpCredential model.

One row per user with TOTP 2FA enrolled. Created by `/auth/two-fa/enroll`
(enabled=False, the user still has to type the first OTP), flipped to
enabled=True by `/auth/two-fa/verify`, deleted by `/auth/two-fa` DELETE.

`secret_encrypted` holds the base32-encoded TOTP secret (Fernet-encrypted
at rest, decrypted on each verification). `backup_codes_hashes` stores
SHA-256 hashes of one-shot recovery codes — the plain codes are returned
to the client exactly once during enrollment (and again during
`/two-fa/backup-codes/regenerate`).

See plan §2.1.5 + ADR-001.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from datetime import timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import EncryptedType

from infrastructure.db.base import Base, _get_encryption_key


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TotpCredential(Base):
    """No TimestampMixin — TOTP credentials are not soft-deleted; DELETE
    /auth/two-fa removes the row outright. Manual created_at / updated_at
    cover audit needs without dragging `is_deleted` / `deleted_at`."""

    __tablename__ = "totp_credentials"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    secret_encrypted: Mapped[str] = mapped_column(
        EncryptedType(String(255), _get_encryption_key), nullable=False,
    )
    backup_codes_hashes: Mapped[list[str]] = mapped_column(
        ARRAY(String(64)), nullable=False, default=list,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow,
    )

    user: Mapped["User"] = relationship("User", back_populates="totp_credential")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<TotpCredential user_id={self.user_id} enabled={self.enabled}>"


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from domains.users.models import User  # noqa: F401
