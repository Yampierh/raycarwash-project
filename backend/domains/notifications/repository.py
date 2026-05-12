from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.notifications.models import DeviceToken, DevicePlatform


class DeviceTokenRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def upsert(
        self,
        user_id: uuid.UUID,
        token: str,
        platform: DevicePlatform,
    ) -> DeviceToken:
        """Register a device token — update last_used_at if it already exists."""
        result = await self._db.execute(
            select(DeviceToken).where(DeviceToken.token == token)
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            existing.user_id = user_id
            existing.last_used_at = datetime.now(timezone.utc)
            await self._db.flush()
            return existing

        device_token = DeviceToken(
            user_id=user_id,
            token=token,
            platform=platform,
        )
        self._db.add(device_token)
        await self._db.flush()
        return device_token

    async def delete_by_token(self, token: str) -> None:
        await self._db.execute(
            delete(DeviceToken).where(DeviceToken.token == token)
        )
        await self._db.flush()

    async def get_tokens_for_user(self, user_id: uuid.UUID) -> list[str]:
        result = await self._db.execute(
            select(DeviceToken.token).where(DeviceToken.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_tokens_for_users(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[str]]:
        """Returns {user_id: [tokens]} for a list of user IDs."""
        if not user_ids:
            return {}
        result = await self._db.execute(
            select(DeviceToken.user_id, DeviceToken.token).where(
                DeviceToken.user_id.in_(user_ids)
            )
        )
        mapping: dict[uuid.UUID, list[str]] = {}
        for row in result.all():
            mapping.setdefault(row.user_id, []).append(row.token)
        return mapping

    async def delete_for_user(self, user_id: uuid.UUID) -> None:
        """Remove all tokens for a user (called on account deletion)."""
        await self._db.execute(
            delete(DeviceToken).where(DeviceToken.user_id == user_id)
        )
        await self._db.flush()
