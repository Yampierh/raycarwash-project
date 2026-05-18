"""
domains/users/payment_method_repository.py — CRUD for `payment_methods`
rows (the local mirror of Stripe payment methods).

Mirrors AddressRepository's shape: only DB access here, default-pivoting
ATOMICITY via a single UPDATE with a CASE expression. The webhook
handler uses upsert_from_snapshot to converge state when Stripe
re-emits payment_method.attached or .updated events.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import and_, case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domains.users.payment_method import PaymentMethod


class PaymentMethodRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ─── Reads ──────────────────────────────────────────────────────────────

    async def list_active(self, user_id: uuid.UUID) -> Sequence[PaymentMethod]:
        stmt = (
            select(PaymentMethod)
            .where(
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_deleted.is_(False),
            )
            .order_by(PaymentMethod.created_at.desc())
        )
        return (await self._db.scalars(stmt)).all()

    async def get_by_id(
        self, user_id: uuid.UUID, pm_id: uuid.UUID
    ) -> PaymentMethod | None:
        stmt = (
            select(PaymentMethod)
            .where(
                PaymentMethod.id == pm_id,
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_deleted.is_(False),
            )
        )
        return await self._db.scalar(stmt)

    async def get_by_stripe_id(
        self, stripe_payment_method_id: str
    ) -> PaymentMethod | None:
        """Webhook entry point — find the local mirror by Stripe PM ID
        regardless of soft-delete status (so we can hard-flip back to
        active if the user re-attaches the same card)."""
        stmt = select(PaymentMethod).where(
            PaymentMethod.stripe_payment_method_id == stripe_payment_method_id
        )
        return await self._db.scalar(stmt)

    async def first_active(
        self, user_id: uuid.UUID, exclude_id: uuid.UUID | None = None
    ) -> PaymentMethod | None:
        conds = [
            PaymentMethod.user_id == user_id,
            PaymentMethod.is_deleted.is_(False),
        ]
        if exclude_id is not None:
            conds.append(PaymentMethod.id != exclude_id)
        stmt = (
            select(PaymentMethod)
            .where(and_(*conds))
            .order_by(PaymentMethod.created_at.asc())
            .limit(1)
        )
        return await self._db.scalar(stmt)

    async def count_active(self, user_id: uuid.UUID) -> int:
        rows = await self.list_active(user_id)
        return len(rows)

    # ─── Writes ─────────────────────────────────────────────────────────────

    def add(self, row: PaymentMethod) -> None:
        self._db.add(row)

    async def soft_delete(
        self, user_id: uuid.UUID, pm_id: uuid.UUID, *, now: datetime
    ) -> bool:
        stmt = (
            update(PaymentMethod)
            .where(
                PaymentMethod.id == pm_id,
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_deleted.is_(False),
            )
            .values(is_deleted=True, deleted_at=now, is_default=False)
        )
        result = await self._db.execute(stmt)
        return (result.rowcount or 0) > 0

    async def soft_delete_by_stripe_id(
        self, stripe_payment_method_id: str, *, now: datetime
    ) -> bool:
        """Webhook payment_method.detached path — flip without needing
        the row in memory or the user_id (it's already encoded by the
        unique stripe_payment_method_id)."""
        stmt = (
            update(PaymentMethod)
            .where(
                PaymentMethod.stripe_payment_method_id == stripe_payment_method_id,
                PaymentMethod.is_deleted.is_(False),
            )
            .values(is_deleted=True, deleted_at=now, is_default=False)
        )
        result = await self._db.execute(stmt)
        return (result.rowcount or 0) > 0

    async def set_default_atomic(
        self, user_id: uuid.UUID, pm_id: uuid.UUID
    ) -> bool:
        """Pivot the default flag through the partial unique index in
        a single UPDATE. See AddressRepository.set_default_atomic for
        the rationale."""
        target = await self.get_by_id(user_id, pm_id)
        if target is None:
            return False
        stmt = (
            update(PaymentMethod)
            .where(
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_deleted.is_(False),
            )
            .values(
                is_default=case(
                    (PaymentMethod.id == pm_id, True),
                    else_=False,
                )
            )
        )
        await self._db.execute(stmt)
        return True

    async def clear_default(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(PaymentMethod)
            .where(
                PaymentMethod.user_id == user_id,
                PaymentMethod.is_default.is_(True),
                PaymentMethod.is_deleted.is_(False),
            )
            .values(is_default=False)
        )
        await self._db.execute(stmt)
