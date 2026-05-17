"""
domains/users/payment_method.py — PaymentMethod model.

Local mirror of the user's Stripe Customer payment methods so the Profile
Hub can render "**** 4242 Visa" without round-tripping to Stripe on every
read. Rows are written by:
  - POST /users/me/payment-methods/setup-intent (user-initiated)
  - payment_method.{attached,detached,updated} webhooks (Stripe-initiated)

ONLY non-PCI fields are persisted. Anything sensitive (full PAN, CVV,
cardholder name when present) stays in Stripe.

Migration: m_007.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class PaymentMethod(TimestampMixin, Base):
    __tablename__ = "payment_methods"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Stripe is the source of truth — pm_xxx is the join key.
    stripe_payment_method_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True,
    )
    # "card" | "us_bank_account" | "apple_pay" | "google_pay". String for
    # forward-compat with future Stripe types.
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    exp_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exp_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    billing_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="payment_methods")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return (
            f"<PaymentMethod id={self.id} user_id={self.user_id} "
            f"brand={self.brand} last4={self.last4}>"
        )


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from domains.users.models import User  # noqa: F401
