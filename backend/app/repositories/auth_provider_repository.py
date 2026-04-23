from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import AuthProvider


class AuthProviderRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_provider(
        self, provider: str, provider_uid: str
    ) -> AuthProvider | None:
        """Return the AuthProvider row for a given provider + uid, or None."""
        stmt = select(AuthProvider).where(
            AuthProvider.provider == provider,
            AuthProvider.provider_uid == provider_uid,
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        provider: str,
        provider_uid: str,
        provider_email: str | None,
    ) -> AuthProvider:
        """Persist a new AuthProvider row and return it."""
        row = AuthProvider(
            user_id=user_id,
            provider=provider,
            provider_uid=provider_uid,
            provider_email=provider_email,
        )
        self._db.add(row)
        await self._db.flush()
        await self._db.refresh(row)
        return row

    async def get_providers_for_user(
        self, user_id: uuid.UUID
    ) -> list[AuthProvider]:
        """Return all social providers linked to a user."""
        stmt = select(AuthProvider).where(AuthProvider.user_id == user_id)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())
