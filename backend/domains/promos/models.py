"""
domains/promos/models.py — promotional code catalogue + redemption ledger.

Plan 24 §3 C-2.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String,
    Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TimestampMixin


class PromoCode(TimestampMixin, Base):
    __tablename__ = "promo_codes"
    __table_args__ = (
        UniqueConstraint("code", name="uq_promo_codes_code"),
        CheckConstraint(
            "discount_type IN ('fixed_cents', 'percent')",
            name="ck_promo_codes_discount_type",
        ),
        CheckConstraint(
            "discount_amount > 0",
            name="ck_promo_codes_discount_positive",
        ),
        CheckConstraint(
            "discount_type != 'percent' OR discount_amount <= 100",
            name="ck_promo_codes_percent_max",
        ),
        CheckConstraint(
            "max_redemptions_per_user >= 1",
            name="ck_promo_codes_per_user_min",
        ),
        Index(
            "ix_promo_codes_active_lookup",
            "code",
            postgresql_where="is_active = true AND is_deleted = false",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # cents (fixed_cents) or percentage 1..100 (percent)
    discount_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    min_order_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_redemptions_per_user: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1",
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
    )

    def __repr__(self) -> str:
        return f"<PromoCode {self.code} {self.discount_type}={self.discount_amount}>"


class AppliedPromoCode(Base):
    __tablename__ = "applied_promo_codes"
    __table_args__ = (
        Index("ix_applied_promo_user", "user_id", "promo_code_id"),
        Index(
            "uq_applied_promo_appointment",
            "promo_code_id", "appointment_id",
            unique=True,
            postgresql_where="appointment_id IS NOT NULL",
        ),
        CheckConstraint(
            "amount_discounted_cents >= 0",
            name="ck_applied_promo_amount_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    promo_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("promo_codes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount_discounted_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
