"""
domains/users/document.py — Document model (Phase 5 chunk Y1).

Backs `/users/me/provider-documents/*`. Stores metadata for KYC
artifacts (insurance certs, business license, certifications, W-9)
that detailers upload during onboarding and re-up periodically.

Files live in the private S3 bucket (ADR-008) — only the s3_key is
persisted here. expires_at powers the daily document_expiry_checker
worker which emails detailers 30 days before lapse.

Although the surface is consumed under /users/me/provider-documents,
the model is keyed on user_id (not provider_user_id) because the
user is the authoritative owner regardless of role. If a detailer
later switches to client-only, the artifacts stay tied to their
account.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class DocumentType(str, enum.Enum):
    """Conventional values for Document.type — stored as String so adding
    a new type doesn't need a migration. The frontend may render unknown
    types as "Other"."""
    INSURANCE = "insurance"
    BUSINESS_LICENSE = "business_license"
    CERTIFICATION = "certification"
    W9 = "w9"
    OTHER = "other"


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_user_type", "user_id", "type"),
        Index("ix_documents_expires_at", "expires_at"),
        CheckConstraint("size_bytes IS NULL OR size_bytes >= 0", name="ck_documents_size_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    s3_key: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="documents")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<Document id={self.id} user_id={self.user_id} type={self.type}>"


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from domains.users.models import User  # noqa: F401
