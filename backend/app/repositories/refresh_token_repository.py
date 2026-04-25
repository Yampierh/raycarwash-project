from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import RefreshToken


class RefreshTokenRepository:
    """
    Repository for refresh tokens with session management capabilities.
    
    FIX: Added methods for session listing and selective revocation
    to support the session management endpoints.
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

    async def revoke_by_raw(self, raw_token: str) -> bool:
        """Revoke a single refresh token by its raw value. Returns True if found."""
        token = await self.get_by_raw(raw_token)
        if token is None:
            return False
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token.id)
            .values(revoked=True)
        )
        await self._db.execute(stmt)
        return True

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a user — forces full re-login."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(revoked=True)
        )
        await self._db.execute(stmt)

    # ------------------------------------------------------------------ #
    #  Session management methods (for GET/DELETE /auth/sessions)           #
    # ------------------------------------------------------------------ #

    async def get_sessions_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[RefreshToken], int]:
        """
        Get active sessions for a user, grouped by family_id.
        Returns (sessions, total_count).
        
        FIX: Enables the session management endpoints.
        """
        # Get distinct family IDs for this user
        family_stmt = (
            select(RefreshToken.family_id)
            .where(RefreshToken.user_id == user_id)
            .distinct()
            .order_by(RefreshToken.family_id)
            .offset(offset)
            .limit(limit)
        )
        family_result = await self._db.execute(family_stmt)
        family_ids = [row[0] for row in family_result.fetchall()]

        if not family_ids:
            return [], 0

        # Get the latest token for each family (for created_at, last_used_at)
        tokens_stmt = (
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.family_id.in_(family_ids))
            .order_by(RefreshToken.family_id, RefreshToken.created_at.desc())
        )
        token_result = await self._db.execute(tokens_stmt)
        tokens = list(token_result.scalars().all())

        # Deduplicate by family_id (keep first/most recent)
        seen = set()
        unique_tokens = []
        for token in tokens:
            if token.family_id not in seen:
                seen.add(token.family_id)
                unique_tokens.append(token)

        # Count total families
        count_stmt = (
            select(RefreshToken.family_id)
            .where(RefreshToken.user_id == user_id)
            .distinct()
        )
        count_result = await self._db.execute(count_stmt)
        total = len(count_result.fetchall())

        return unique_tokens, total

    async def get_session_by_family(
        self,
        user_id: uuid.UUID,
        family_id: uuid.UUID,
    ) -> RefreshToken | None:
        """Get a session by family_id for a user."""
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.family_id == family_id)
            .order_by(RefreshToken.created_at.desc())
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_session(
        self,
        user_id: uuid.UUID,
        family_id: uuid.UUID,
    ) -> bool:
        """
        Revoke a specific session (family_id).
        Returns True if found and revoked.
        
        FIX: Enables selective session revocation.
        """
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.family_id == family_id)
            .values(revoked=True)
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0
