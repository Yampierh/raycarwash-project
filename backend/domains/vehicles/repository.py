from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domains.vehicles.models import Vehicle


class VehicleRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, vehicle_id: uuid.UUID) -> Vehicle | None:
        stmt = select(Vehicle).where(
            Vehicle.id == vehicle_id,
            Vehicle.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[Vehicle]:
        stmt = (
            select(Vehicle)
            .where(Vehicle.owner_id == owner_id, Vehicle.is_deleted.is_(False))
            .order_by(Vehicle.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, vehicle: Vehicle) -> Vehicle:
        self._db.add(vehicle)
        await self._db.flush()
        await self._db.refresh(vehicle)
        return vehicle

    async def soft_delete(self, vehicle_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
        stmt = (
            update(Vehicle)
            .where(
                Vehicle.id == vehicle_id,
                Vehicle.owner_id == owner_id,
                Vehicle.is_deleted.is_(False),
            )
            .values(is_deleted=True, deleted_at=datetime.utcnow())
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount > 0

    async def update(self, vehicle_id: uuid.UUID, owner_id: uuid.UUID, **kwargs) -> Vehicle | None:
        stmt = (
            update(Vehicle)
            .where(
                Vehicle.id == vehicle_id,
                Vehicle.owner_id == owner_id,
                Vehicle.is_deleted.is_(False),
            )
            .values(**kwargs)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        if result.rowcount > 0:
            return await self.get_by_id(vehicle_id)
        return None
