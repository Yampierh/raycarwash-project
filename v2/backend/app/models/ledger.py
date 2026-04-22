from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.models import Base


# ------------------------------------------------------------------ #
#  Enums                                                              #
# ------------------------------------------------------------------ #

class LedgerEntryType(str, enum.Enum):
    AUTHORIZATION = "authorization"  # Card hold placed before service starts
    CAPTURE       = "capture"        # Hold captured once detailer is assigned
    CHARGE        = "charge"         # Direct charge (platform fee, commission)
    REFUND        = "refund"         # Refund — always a new row, never modifies CHARGE
    ADJUSTMENT    = "adjustment"     # Admin-applied manual correction
    PAYOUT        = "payout"         # Disbursement to detailer


class AssignmentStatus(str, enum.Enum):
    OFFERED  = "offered"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    TIMEOUT  = "timeout"


# ------------------------------------------------------------------ #
#  PaymentLedger                                                      #
# ------------------------------------------------------------------ #

class PaymentLedger(Base):
    """
    Append-only financial ledger.

    INVARIANT: This table is write-once. No UPDATE, no DELETE, no is_deleted flag.
    Corrections are applied via LedgerRevision (which points to a new corrective entry).

    Balance for an appointment:
        SELECT SUM(amount_cents) FROM payment_ledger WHERE appointment_id = X
    """
    __tablename__ = "payment_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    detailer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    entry_type: Mapped[LedgerEntryType] = mapped_column(
        Enum(LedgerEntryType, name="ledger_entry_type"), nullable=False
    )
    amount_cents: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Positive = inflow, Negative = outflow (refunds, payouts)"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")

    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stripe_charge_id: Mapped[str | None]          = mapped_column(String(100), nullable=True)
    stripe_refund_id: Mapped[str | None]          = mapped_column(String(100), nullable=True)

    # Self-referential: refund/adjustment entries point to the original charge
    related_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_ledger.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reason: Mapped[str | None]    = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict]       = mapped_column("metadata", JSONB, nullable=False, default=dict)

    # Immutable timestamps — no updated_at
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User or system service account that created this entry",
    )

    __table_args__ = (
        # Strongly consistent: prevent duplicate authorization for the same payment intent
        UniqueConstraint(
            "stripe_payment_intent_id",
            name="uq_ledger_stripe_auth",
            postgresql_where="entry_type = 'authorization' AND stripe_payment_intent_id IS NOT NULL",
        ),
    )


# ------------------------------------------------------------------ #
#  LedgerSeal                                                         #
# ------------------------------------------------------------------ #

class LedgerSeal(Base):
    """
    Daily seal: closes a calendar day's ledger entries as read-only.

    After sealing, any correction for that day must go through LedgerRevision.
    The checksum (SHA-256 of all entry IDs sorted alphabetically) allows
    independent verification that the sealed set is complete and unmodified.
    """
    __tablename__ = "ledger_seals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sealed_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    entry_count: Mapped[int]  = mapped_column(Integer, nullable=False)
    total_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str]     = mapped_column(String(64), nullable=False)  # SHA-256 hex
    sealed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    sealed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="System service account or admin that triggered the seal",
    )


# ------------------------------------------------------------------ #
#  LedgerRevision                                                     #
# ------------------------------------------------------------------ #

class LedgerRevision(Base):
    """
    Post-seal correction record.

    When an error is found in a sealed day, a new PaymentLedger entry
    is created with the correct amount, and a LedgerRevision ties the
    original (incorrect) entry to the corrective entry.

    The original entry is NEVER modified — only referenced here.
    """
    __tablename__ = "ledger_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sealed_date: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="Which sealed calendar day is being corrected"
    )
    original_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_ledger.id", ondelete="RESTRICT"),
        nullable=False,
    )
    correction_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payment_ledger.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str]        = mapped_column(Text, nullable=False)
    approved_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Admin user who approved this post-seal correction",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# ------------------------------------------------------------------ #
#  AppointmentAssignment                                              #
# ------------------------------------------------------------------ #

class AppointmentAssignment(Base):
    """
    Tracks each detailer offer made during the assignment process.

    One appointment may have multiple rows (one per candidate attempted).
    Only one row will have status=accepted.
    """
    __tablename__ = "appointment_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    detailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status"), nullable=False
    )
    offer_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
