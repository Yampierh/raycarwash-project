from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Addon, Service


class ServiceRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, service_id: uuid.UUID) -> Service | None:
        stmt = select(Service).where(
            Service.id == service_id,
            Service.is_active.is_(True),
            Service.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> list[Service]:
        stmt = (
            select(Service)
            .where(Service.is_active.is_(True), Service.is_deleted.is_(False))
            .order_by(Service.base_price_cents.asc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())


class AddonRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_active(self) -> list[Addon]:
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
        if not addon_ids:
            return []
        stmt = select(Addon).where(
            Addon.id.in_(addon_ids),
            Addon.is_active.is_(True),
            Addon.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        rows = {row.id: row for row in result.scalars().all()}
        return [rows[aid] for aid in addon_ids if aid in rows]
