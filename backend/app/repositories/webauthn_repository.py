# app/repositories/webauthn_repository.py
#
# All database operations for the `webauthn_credentials` table.
# Follows the same Repository pattern as user_repository.py:
#   - One instance per request, sharing the request-scoped AsyncSession.
#   - No business logic here — just raw DB queries.

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import WebAuthnCredential


class WebAuthnRepository:
    """Data access layer for FIDO2/WebAuthn credentials."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_credentials_by_user(
        self, user_id: uuid.UUID
    ) -> list[WebAuthnCredential]:
        """Return all passkey credentials registered for a user."""
        stmt = select(WebAuthnCredential).where(
            WebAuthnCredential.user_id == user_id
        )
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_credential_by_id(
        self, credential_id: bytes
    ) -> WebAuthnCredential | None:
        """
        Fetch a single credential by its raw credential_id bytes.

        Used during authentication to look up the stored public key and
        sign_count before calling verify_authentication_response().
        """
        stmt = select(WebAuthnCredential).where(
            WebAuthnCredential.credential_id == credential_id
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_credential(
        self, credential: WebAuthnCredential
    ) -> WebAuthnCredential:
        """Persist a newly-registered passkey credential."""
        self._db.add(credential)
        await self._db.flush()
        return credential

    async def update_sign_count(
        self,
        credential_id: bytes,
        sign_count: int,
        last_used_at: datetime,
    ) -> None:
        """
        Update the sign_count and last_used_at after a successful authentication.

        The sign_count is a replay-attack mitigation: py_webauthn raises if the
        received count is not greater than the stored count (for counters > 0).
        """
        stmt = (
            select(WebAuthnCredential)
            .where(WebAuthnCredential.credential_id == credential_id)
        )
        result = await self._db.execute(stmt)
        cred = result.scalar_one_or_none()
        if cred:
            cred.sign_count = sign_count
            cred.last_used_at = last_used_at
            await self._db.flush()

    async def delete_credential(
        self, credential_id: bytes, user_id: uuid.UUID
    ) -> bool:
        """
        Delete a passkey by credential_id, scoped to user_id for safety.

        Returns True if a row was deleted, False if not found.
        """
        stmt = delete(WebAuthnCredential).where(
            WebAuthnCredential.credential_id == credential_id,
            WebAuthnCredential.user_id == user_id,
        )
        result = await self._db.execute(stmt)
        return result.rowcount > 0
