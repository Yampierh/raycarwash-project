from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import RefreshToken


class RefreshTokenRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def _hash(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    async def create(
        self,
        user_id: uuid.UUID,
        raw_token: str,
        family_id: uuid.UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        """Store a new refresh token (only the SHA-256 hash is persisted)."""
        row = RefreshToken(
            user_id=user_id,
            token_hash=self._hash(raw_token),
            family_id=family_id,
            expires_at=expires_at,
        )
        self._db.add(row)
        await self._db.flush()
        return row

    async def get_by_raw(self, raw_token: str) -> RefreshToken | None:
        """Look up a refresh token by its raw value."""
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == self._hash(raw_token)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_used(self, token_id: uuid.UUID) -> None:
        """Stamp used_at so this token can never be reused."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._db.execute(stmt)

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        """Mark every token in this rotation family as revoked (theft response)."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .values(revoked=True)
        )
        await self._db.execute(stmt)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a user — forces full re-login."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(revoked=True)
        )
        await self._db.execute(stmt)
