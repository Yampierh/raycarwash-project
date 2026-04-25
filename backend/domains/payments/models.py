from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
    text as sa_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base


class FareEstimate(Base):
    __tablename__ = "fare_estimates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("services.id", ondelete="RESTRICT"), nullable=False,
    )
    vehicle_sizes: Mapped[list] = mapped_column(JSONB, nullable=False)
    client_lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    client_lng: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    base_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    surge_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("1.0"),
    )
    estimated_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    nearby_detailers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fare_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<FareEstimate id={self.id} price={self.estimated_price_cents}>"


class ProcessedWebhook(Base):
    __tablename__ = "processed_webhooks"

    stripe_event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=sa_text("now()"),
    )

    def __repr__(self) -> str:
        return f"<ProcessedWebhook event={self.stripe_event_id} type={self.event_type}>"


class PaymentLedger(Base):
    """Append-only financial ledger. No updates, no soft-delete."""
    __tablename__ = "payment_ledger"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    entry_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="AUTHORIZATION | CAPTURE | REFUND | PAYOUT | CHARGE_COMMISSION",
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True,
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<PaymentLedger {self.entry_type} {self.amount_cents}¢ appt={self.appointment_id}>"


class LedgerSeal(Base):
    __tablename__ = "ledger_seals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seal_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    entry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<LedgerSeal {self.seal_date} entries={self.entry_count}>"


class LedgerRevision(Base):
    __tablename__ = "ledger_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_ledger.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<LedgerRevision entry={self.original_entry_id}>"
