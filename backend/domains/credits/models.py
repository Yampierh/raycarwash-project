"""
domains/credits/models.py — comp-credit ledger.

Each row is a credit-affecting event. Positive `amount_cents` is an issue
(money the platform owes the user), negative is a consumption or revoke.
The user's balance is the sum of `amount_cents` over their active rows.

Plan 24 W2-E. New entries land via `POST /api/v1/admin/customers/{id}/credits`.
Consumption hooks (apply credit at checkout) are deferred to Wave 4.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class CustomerCredit(TimestampMixin, Base):
    __tablename__ = "customer_credits"
    __table_args__ = (
        # Non-zero rows only — a 0¢ entry is meaningless.
        CheckConstraint("amount_cents != 0", name="ck_customer_credits_amount_nonzero"),
        CheckConstraint(
            "status IN ('active', 'consumed', 'expired', 'revoked')",
            name="ck_customer_credits_status",
        ),
        CheckConstraint(
            "source IN ('admin_comp', 'promo', 'referral', 'refund', 'adjustment')",
            name="ck_customer_credits_source",
        ),
        # Wallet-balance queries scan active rows per user. Partial index.
        Index(
            "ix_customer_credits_user_active",
            "user_id",
            postgresql_where="status = 'active'",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="USD", server_default="USD",
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="admin_comp",
        server_default="admin_comp",
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default="active",
    )
    issued_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin who issued the credit; NULL for system-generated.",
    )
    related_appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
        comment="Set for refund-driven credits so we can chain them to the originating appointment.",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<CustomerCredit user_id={self.user_id} "
            f"amount={self.amount_cents} status={self.status}>"
        )
