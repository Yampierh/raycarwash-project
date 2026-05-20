"""
app/db/seed_cities.py — Plan 24 §3 P-2 / §5.2 A-1.

The 5 launch markets from the design package
(`provider-signup.jsx` step 3 city picker). Idempotent: skip rows
whose `code` already exists.

Fort Wayne is `active` (current operating city). The other 4 are
`pilot` — listed on the signup picker but only accepting applications
in early waves. Status governs whether matching + checkout enable
them; flip via admin dashboard later.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.locations.models import City, CityStatus

logger = logging.getLogger(__name__)


_CITIES: list[dict] = [
    {
        "code": "fwa",
        "name": "Fort Wayne",
        "state": "IN",
        "timezone": "America/Indiana/Indianapolis",
        "status": CityStatus.ACTIVE.value,
        "sort_order": 10,
    },
    {
        "code": "ind",
        "name": "Indianapolis",
        "state": "IN",
        "timezone": "America/Indiana/Indianapolis",
        "status": CityStatus.PILOT.value,
        "sort_order": 20,
    },
    {
        "code": "col",
        "name": "Columbus",
        "state": "OH",
        "timezone": "America/New_York",
        "status": CityStatus.PILOT.value,
        "sort_order": 30,
    },
    {
        "code": "cin",
        "name": "Cincinnati",
        "state": "OH",
        "timezone": "America/New_York",
        "status": CityStatus.PILOT.value,
        "sort_order": 40,
    },
    {
        "code": "lou",
        "name": "Louisville",
        "state": "KY",
        "timezone": "America/Kentucky/Louisville",
        "status": CityStatus.PILOT.value,
        "sort_order": 50,
    },
]


async def seed_cities(db: AsyncSession) -> None:
    """Idempotent upsert keyed on `code` (UNIQUE)."""
    seeded = 0
    for entry in _CITIES:
        existing = await db.execute(
            select(City).where(
                City.code == entry["code"],
                City.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none():
            continue
        db.add(City(**entry))
        seeded += 1
    await db.commit()
    logger.info("Cities seed complete — %d new city(ies) inserted.", seeded)
