from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text,
    UniqueConstraint, text as sa_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base


class FareEstimate(Base):
    __tablename__ = "fare_estimates"
    __table_args__ = (
        Index("ix_fare_estimates_expires_at", "expires_at"),
        CheckConstraint("base_price_cents >= 0", name="ck_fare_estimates_base_price_nonnegative"),
        CheckConstraint("estimated_price_cents >= 0", name="ck_fare_estimates_estimated_price_nonnegative"),
        CheckConstraint("surge_multiplier >= 1", name="ck_fare_estimates_surge_multiplier_min"),
        CheckConstraint("nearby_detailers_count >= 0", name="ck_fare_estimates_nearby_count_nonnegative"),
    )

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
    __table_args__ = (
        Index("ix_payment_ledger_type_created", "entry_type", "created_at"),
        CheckConstraint("currency = lower(currency)", name="ck_payment_ledger_currency_lowercase"),
        CheckConstraint("amount_cents >= 0", name="ck_payment_ledger_amount_nonnegative"),
    )

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
    __table_args__ = (
        CheckConstraint("entry_count >= 0", name="ck_ledger_seals_entry_count_nonnegative"),
        CheckConstraint("length(sha256_hash) = 64", name="ck_ledger_seals_sha256_length"),
    )

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


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        Index("ix_refunds_appointment_created", "appointment_id", "created_at"),
        Index("ix_refunds_status_created", "status", "created_at"),
        UniqueConstraint("stripe_refund_id", name="uq_refunds_stripe_refund_id"),
        CheckConstraint("amount_cents >= 0", name="ck_refunds_amount_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    payment_ledger_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payment_ledger.id", ondelete="SET NULL"), nullable=True,
    )
    stripe_refund_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd", server_default="usd")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default="pending")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ProviderPayout(Base):
    __tablename__ = "provider_payouts"
    __table_args__ = (
        Index("ix_provider_payouts_provider_created", "provider_profile_id", "created_at"),
        Index("ix_provider_payouts_status_created", "status", "created_at"),
        UniqueConstraint("stripe_payout_id", name="uq_provider_payouts_stripe_payout_id"),
        CheckConstraint("amount_cents >= 0", name="ck_provider_payouts_amount_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    stripe_payout_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd", server_default="usd")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default="pending")
    arrival_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
