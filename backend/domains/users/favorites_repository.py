"""
domains/users/favorites_repository.py — CRUD for `client_favorites` rows.

The UNIQUE (user_id, provider_user_id) constraint from m_008 makes add
naturally idempotent — we use INSERT ... ON CONFLICT DO NOTHING so a
re-favor is a 200 no-op rather than a 409, matching the "tap-tap-tap"
mobile UX where the user just wants the pin to be ON.

Reads join Provider+User so the response can render display_name +
avatar + rating without a second query per row.
"""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from domains.providers.models import ProviderProfile
from domains.users.client_favorite import ClientFavorite
from domains.users.models import User


class FavoritesRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_user(
        self, user_id: uuid.UUID
    ) -> Sequence[tuple[ClientFavorite, User | None, ProviderProfile | None]]:
        """One row per favorite. ProviderUser / ProviderProfile come in via
        outer joins so half-onboarded providers still surface in the list
        (with display_name / avatar / rating = None)."""
        ProviderUser = aliased(User, name="provider_user")
        stmt = (
            select(ClientFavorite, ProviderUser, ProviderProfile)
            .join(
                ProviderUser,
                ProviderUser.id == ClientFavorite.provider_user_id,
                isouter=True,
            )
            .join(
                ProviderProfile,
                ProviderProfile.user_id == ClientFavorite.provider_user_id,
                isouter=True,
            )
            .where(ClientFavorite.user_id == user_id)
            .order_by(ClientFavorite.created_at.desc())
        )
        result = await self._db.execute(stmt)
        return result.all()

    async def add(
        self, user_id: uuid.UUID, provider_user_id: uuid.UUID
    ) -> bool:
        """Insert; returns True iff a new row landed (False on duplicate).

        Caller can use the return value to decide between
        AuditAction.FAVORITE_ADDED (real new pin) vs no audit (no-op
        re-favor)."""
        stmt = (
            pg_insert(ClientFavorite)
            .values(
                user_id=user_id,
                provider_user_id=provider_user_id,
                # m_008 leaves created_at without server_default; populate
                # via SQLAlchemy default at INSERT time.
            )
            .on_conflict_do_nothing(
                index_elements=["user_id", "provider_user_id"]
            )
        )
        from datetime import datetime, timezone
        stmt = stmt.values(created_at=datetime.now(timezone.utc))
        result = await self._db.execute(stmt)
        return (result.rowcount or 0) > 0

    async def remove(
        self, user_id: uuid.UUID, provider_user_id: uuid.UUID
    ) -> bool:
        stmt = delete(ClientFavorite).where(
            ClientFavorite.user_id == user_id,
            ClientFavorite.provider_user_id == provider_user_id,
        )
        result = await self._db.execute(stmt)
        return (result.rowcount or 0) > 0
