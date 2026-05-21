"""
domains/promos/service.py — promo validation + preview.

Validation is a function of the promo row + the user's prior redemption
count. The actual "redeem" (insert into applied_promo_codes) is owned
by the booking pipeline, not this module — we only model the read side
here so the frontend can show "promo applied" UI before checkout.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.promos.models import AppliedPromoCode, PromoCode


class PromoService:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def _normalize_code(code: str) -> str:
        """Codes are stored case-sensitive but conventionally upper. Trim
        whitespace + uppercase for lookup so 'new10' and ' NEW10 ' both
        match a row stored as 'NEW10'."""
        return code.strip().upper()

    async def lookup(
        self, code: str, *, user_id: uuid.UUID | None = None,
    ) -> tuple[PromoCode | None, str | None, int | None]:
        """Return (promo, ineligible_reason, remaining_per_user).
        `ineligible_reason` is None when the promo is currently usable
        (modulo per-user redemption); `remaining_per_user` is computed
        only when `user_id` is provided."""
        normalized = self._normalize_code(code)
        promo = (await self._db.execute(
            select(PromoCode).where(
                PromoCode.code == normalized,
                PromoCode.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if promo is None:
            return None, "not_found", None

        reason = self._global_ineligible_reason(promo)
        remaining = None
        if user_id is not None:
            redeemed = await self._user_redemptions(promo.id, user_id)
            remaining = max(0, promo.max_redemptions_per_user - redeemed)
            if reason is None and remaining == 0:
                reason = "max_redemptions_per_user_reached"

        return promo, reason, remaining

    async def preview(
        self,
        *,
        code: str,
        subtotal_cents: int,
        user_id: uuid.UUID | None = None,
    ) -> tuple[bool, int, int, str | None]:
        """Return (eligible, discount_cents, final_cents, reason)."""
        promo, reason, _ = await self.lookup(code, user_id=user_id)
        if promo is None:
            return False, 0, subtotal_cents, reason or "not_found"
        if reason is not None:
            return False, 0, subtotal_cents, reason
        if promo.min_order_cents and subtotal_cents < promo.min_order_cents:
            return False, 0, subtotal_cents, "below_min_order"

        if promo.discount_type == "fixed_cents":
            discount = min(promo.discount_amount, subtotal_cents)
        else:  # percent
            discount = (subtotal_cents * promo.discount_amount) // 100

        final = max(0, subtotal_cents - discount)
        return True, discount, final, None

    # ── internals ─────────────────────────────────────────────────── #

    @staticmethod
    def _global_ineligible_reason(promo: PromoCode) -> str | None:
        now = datetime.now(timezone.utc)
        if not promo.is_active:
            return "inactive"
        if promo.valid_from and now < promo.valid_from:
            return "not_yet_valid"
        if promo.valid_until and now > promo.valid_until:
            return "expired"
        return None

    async def _user_redemptions(
        self, promo_id: uuid.UUID, user_id: uuid.UUID,
    ) -> int:
        stmt = select(func.count(AppliedPromoCode.id)).where(
            AppliedPromoCode.promo_code_id == promo_id,
            AppliedPromoCode.user_id == user_id,
        )
        return int((await self._db.execute(stmt)).scalar_one())
