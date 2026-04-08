# app/repositories/addon_repository.py  —  Sprint 5

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Addon


class AddonRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_active(self) -> list[Addon]:
        """Return all active addons ordered by name."""
        stmt = (
            select(Addon)
            .where(Addon.is_active.is_(True), Addon.is_deleted.is_(False))
            .order_by(Addon.name.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, addon_id: uuid.UUID) -> Addon | None:
        stmt = select(Addon).where(
            Addon.id == addon_id,
            Addon.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many_by_ids(self, addon_ids: list[uuid.UUID]) -> list[Addon]:
        """Fetch multiple addons in one query, preserving order."""
        if not addon_ids:
            return []
        stmt = select(Addon).where(
            Addon.id.in_(addon_ids),
            Addon.is_active.is_(True),
            Addon.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        rows = {row.id: row for row in result.scalars().all()}
        # Preserve caller order and detect missing IDs
        return [rows[aid] for aid in addon_ids if aid in rows]
