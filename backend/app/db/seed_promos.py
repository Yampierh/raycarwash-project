"""
app/db/seed_promos.py — Plan 24 §3 C-2.

Seeds the system promo catalogue. Idempotent: skips rows whose `code`
already exists.

NEW10 is the welcome credit shown in the customer signup step-5 design.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.promos.models import PromoCode

logger = logging.getLogger(__name__)


_PROMOS: list[dict] = [
    {
        "code": "NEW10",
        "description": "Welcome credit — $10 off your first booking.",
        "discount_type": "fixed_cents",
        "discount_amount": 1_000,
        "min_order_cents": 2_000,
        "max_redemptions": None,
        "max_redemptions_per_user": 1,
        "is_active": True,
    },
]


async def seed_promos(db: AsyncSession) -> None:
    """Idempotent upsert keyed on `code` (UNIQUE)."""
    seeded = 0
    for entry in _PROMOS:
        existing = await db.execute(
            select(PromoCode).where(
                PromoCode.code == entry["code"],
                PromoCode.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(PromoCode(**entry))
        seeded += 1
    await db.commit()
    logger.info("Promo seed complete — %d new promo(s) inserted.", seeded)
