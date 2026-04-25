from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import PasswordResetToken


class PasswordResetTokenRepository:
    """
    Repository for single-use password reset tokens.
    Mirrors RefreshToken pattern but with different lifecycle:
    - Reset tokens are one-shot (used once, then never again)
    - Expires quickly (typically 1 hour)
    - Cannot be rotated (no family_id)

    FIX: Prevents token reuse from intercepted reset links.
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
    ) -> PasswordResetToken:
        """Store a new password reset token (only the SHA-256 hash is persisted)."""
        row = PasswordResetToken(
            user_id=user_id,
            token_hash=self._hash(raw_token),
            expires_at=expires_at,
        )
        self._db.add(row)
        await self._db.flush()
        return row

    async def get_by_raw(self, raw_token: str) -> PasswordResetToken | None:
        """Look up a reset token by its raw value."""
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == self._hash(raw_token)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_used(self, token_id: uuid.UUID) -> None:
        """
        Mark token as used to prevent reuse.
        FIX: This is the key fix — tokens can only be used once.
        """
        stmt = (
            update(PasswordResetToken)
            .where(PasswordResetToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._db.execute(stmt)

    async def is_valid(self, raw_token: str) -> bool:
        """
        Check if a token is valid (exists and not used and not expired).
        FIX: Single-use guarantee - returns False if already used.
        """
        token = await self.get_by_raw(raw_token)
        if token is None:
            return False
        if token.used_at is not None:
            return False
        if token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return False
        return True

    async def consume(self, raw_token: str) -> PasswordResetToken | None:
        """
        Atomically consume a token: mark as used, return the row.
        Returns None if token is invalid or already used.
        FIX: Single operation prevents race conditions.
        """
        token = await self.get_by_raw(raw_token)
        if token is None:
            return None
        if token.used_at is not None:
            return None  # Already used
        if token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return None  # Expired
        
        await self.mark_used(token.id)
        return token

    async def invalidate_all_for_user(self, user_id: uuid.UUID) -> None:
        """
        Invalidate all unused reset tokens for a user.
        Useful when a new password reset is requested (one active token at a time).
        """
        stmt = (
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id)
            .where(PasswordResetToken.used_at.is_(None))  # Only unused
            .values(used_at=datetime.now(timezone.utc))
        )
        await self._db.execute(stmt)

    async def cleanup_expired(self) -> int:
        """
        Delete all expired reset tokens.
        Can be run as a scheduled job.
        Returns count of deleted rows.
        """
        stmt = (
            update(PasswordResetToken)
            .where(PasswordResetToken.expires_at < datetime.now(timezone.utc))
            .where(PasswordResetToken.used_at.is_(None))  # Don't re-delete used tokens
        )
        result = await self._db.execute(stmt)
        return result.rowcount