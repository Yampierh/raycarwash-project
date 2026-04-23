from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.models import Base


class PaymentLedger(Base):
    """
    Append-only financial ledger.
    No updated_at, no is_deleted, no soft-delete — ever.
    Corrections are recorded as LedgerRevision rows, never as UPDATEs.
    """

    __tablename__ = "payment_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    entry_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="AUTHORIZATION | CAPTURE | REFUND | PAYOUT | CHARGE_COMMISSION",
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PaymentLedger {self.entry_type} {self.amount_cents}¢ appt={self.appointment_id}>"


class LedgerSeal(Base):
    """
    Nightly cryptographic seal over the previous day's ledger entries.
    Once sealed, entries are considered immutable at the business level.
    """

    __tablename__ = "ledger_seals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    seal_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA-256 of all entry_ids (sorted, concatenated) for that day.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<LedgerSeal {self.seal_date} entries={self.entry_count}>"


class LedgerRevision(Base):
    """
    Audit record when a ledger entry requires a business-level correction note.
    Does NOT modify the original entry — the original row is immutable.
    """

    __tablename__ = "ledger_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_ledger.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<LedgerRevision entry={self.original_entry_id}>"
