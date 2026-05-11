from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import EmailVerificationToken


class EmailVerificationTokenRepository:
    """
    Repository for single-use email verification tokens stored in the DB.

    Replaces the previous stateless JWT approach so tokens can be:
    - Invalidated when a new verification is requested (one active token at a time)
    - Consumed on first use (replay protection)
    - Cleaned up by the background token cleanup worker
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @staticmethod
    def _hash(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    async def create(
        self,
        user_id: uuid.UUID,
        raw_token: str,
        expires_at: datetime,
    ) -> EmailVerificationToken:
        """Store a new email verification token (only SHA-256 hash is persisted)."""
        row = EmailVerificationToken(
            user_id=user_id,
            token_hash=self._hash(raw_token),
            expires_at=expires_at,
        )
        self._db.add(row)
        await self._db.flush()
        return row

    async def get_by_raw(self, raw_token: str) -> EmailVerificationToken | None:
        """Look up a token by its raw value."""
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == self._hash(raw_token)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def consume(self, raw_token: str) -> EmailVerificationToken | None:
        """
        Atomically validate and consume a token.
        Returns the token row if valid, None if invalid/used/expired.
        """
        token = await self.get_by_raw(raw_token)
        if token is None:
            return None
        if token.used_at is not None:
            return None
        if token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return None

        stmt = (
            update(EmailVerificationToken)
            .where(EmailVerificationToken.id == token.id)
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._db.execute(stmt)
        return token

    async def invalidate_all_for_user(self, user_id: uuid.UUID) -> None:
        """
        Mark all unused tokens for a user as used.
        Called before issuing a new token so only one is active at a time.
        """
        stmt = (
            update(EmailVerificationToken)
            .where(EmailVerificationToken.user_id == user_id)
            .where(EmailVerificationToken.used_at.is_(None))
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._db.execute(stmt)
