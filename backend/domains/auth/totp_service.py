"""
domains/auth/totp_service.py — TOTP 2FA lifecycle for /auth/two-fa/*.

Four flows:
  enroll       — generate a fresh secret, persist enabled=False, return
                 the otpauth:// URL + 10 plain backup codes. Idempotent
                 within an in-flight enrollment (re-calling resets the
                 secret + codes).
  verify       — accept the user's first OTP from their authenticator
                 app, flip enabled=True.
  disable      — drop the row entirely.
  regenerate_backup_codes — replace the codes (the plain set is shown
                            exactly once, hashes are stored).

The TOTP secret is encrypted at rest via EncryptedType. Backup codes are
SHA-256 hashed; the plain form is only ever returned in the API
response.

Step-up is enforced at the router layer (enroll / disable / regenerate
require step-up; verify does not because it's the step-up event itself).
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone

import pyotp
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.middleware.audit_context import get_audit_context
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.totp_credential import TotpCredential
from domains.users.models import User

logger = logging.getLogger(__name__)


_BACKUP_CODE_COUNT = 10
_TOTP_DIGITS = 6
_TOTP_PERIOD_SECONDS = 30
# Window of ±1 period — covers clock drift up to ~30s in either direction
# without making brute force easier.
_TOTP_VALID_WINDOW = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def _generate_backup_codes(n: int = _BACKUP_CODE_COUNT) -> list[str]:
    """Return `n` plain codes formatted like A1B2-C3D4 — 8 base32 chars
    split by a hyphen for legibility. The chars are uppercase to remove
    ambiguity with typing on mobile keyboards."""
    alphabet = "ABCDEFGHJKMNPQRSTVWXYZ23456789"  # Crockford-ish, no 0/1/I/O/L
    codes: list[str] = []
    for _ in range(n):
        raw = "".join(secrets.choice(alphabet) for _ in range(8))
        codes.append(f"{raw[:4]}-{raw[4:]}")
    return codes


class TotpError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


class TotpService:
    def __init__(self, db: AsyncSession, request: Request) -> None:
        self.db = db
        self.request = request
        self.audit = AuditRepository(db)
        self.settings = get_settings()

    # ────── enroll ───────────────────────────────────────────────────────

    async def enroll(self, user: User) -> dict:
        """Generate a secret + backup codes. Returns the plain values so
        the client can show the QR + recovery codes ONCE; we never expose
        them again."""
        cred = await self._get_credential(user.id)
        secret = pyotp.random_base32()
        plain_codes = _generate_backup_codes()
        hashed_codes = [_hash_backup_code(c) for c in plain_codes]

        if cred is None:
            cred = TotpCredential(
                user_id=user.id,
                secret_encrypted=secret,
                backup_codes_hashes=hashed_codes,
                enabled=False,
            )
            self.db.add(cred)
        else:
            # Re-enrollment before /verify — caller may have lost the QR.
            cred.secret_encrypted = secret
            cred.backup_codes_hashes = hashed_codes
            cred.enabled = False
            cred.updated_at = _utcnow()

        await self.db.flush()

        # Standard otpauth URI — Authy / Google Authenticator render the
        # QR straight from the issuer + label format.
        issuer = self.settings.PROJECT_NAME
        otpauth_uri = pyotp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name=issuer,
        )

        await self.audit.log(
            action=AuditAction.TWO_FA_ENABLED,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            metadata={"step": "enrolled"},
            audit_ctx=get_audit_context(self.request),
        )

        return {
            "secret": secret,
            "otpauth_uri": otpauth_uri,
            "backup_codes": plain_codes,
        }

    # ────── verify ───────────────────────────────────────────────────────

    async def verify(self, user: User, code: str) -> None:
        """Accept the first OTP, flip enabled=True. A backup code is also
        accepted — useful if the user lost the authenticator before
        finishing enrollment."""
        cred = await self._get_credential(user.id)
        if cred is None:
            raise TotpError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "No pending TOTP enrollment. Call /auth/two-fa/enroll first.",
            )

        if self._matches_code(cred, code):
            cred.enabled = True
            cred.last_used_at = _utcnow()
            cred.updated_at = _utcnow()
            await self.db.flush()
            await self.audit.log(
                action=AuditAction.TWO_FA_ENABLED,
                entity_type="user",
                entity_id=str(user.id),
                actor_id=user.id,
                metadata={"step": "verified"},
                audit_ctx=get_audit_context(self.request),
            )
            return

        raise TotpError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_failed",
            "Incorrect code. Please try again.",
        )

    # ────── disable ──────────────────────────────────────────────────────

    async def disable(self, user: User) -> None:
        cred = await self._get_credential(user.id)
        if cred is None:
            return  # idempotent — nothing to disable
        await self.db.delete(cred)
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.TWO_FA_DISABLED,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            audit_ctx=get_audit_context(self.request),
        )

    # ────── regenerate backup codes ──────────────────────────────────────

    async def regenerate_backup_codes(self, user: User) -> list[str]:
        cred = await self._get_credential(user.id)
        if cred is None or not cred.enabled:
            raise TotpError(
                status.HTTP_409_CONFLICT,
                "conflict",
                "2FA is not enabled. Call /auth/two-fa/enroll + /verify first.",
            )
        plain = _generate_backup_codes()
        cred.backup_codes_hashes = [_hash_backup_code(c) for c in plain]
        cred.updated_at = _utcnow()
        await self.db.flush()
        await self.audit.log(
            action=AuditAction.TWO_FA_ENABLED,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            metadata={"step": "backup_codes_regenerated"},
            audit_ctx=get_audit_context(self.request),
        )
        return plain

    # ────── helpers ──────────────────────────────────────────────────────

    async def _get_credential(self, user_id) -> TotpCredential | None:
        stmt = select(TotpCredential).where(TotpCredential.user_id == user_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    def _matches_code(self, cred: TotpCredential, code: str) -> bool:
        """Try the TOTP first, then the backup code list. Used backup
        codes are removed in place — single use."""
        normalized = code.strip().replace(" ", "").replace("-", "")

        # 6-digit numeric → TOTP
        if normalized.isdigit() and len(normalized) == _TOTP_DIGITS:
            totp = pyotp.TOTP(cred.secret_encrypted)
            return totp.verify(normalized, valid_window=_TOTP_VALID_WINDOW)

        # 8 base32 chars (with optional hyphen) → backup code
        hashed = _hash_backup_code(code)
        for stored in cred.backup_codes_hashes:
            if secrets.compare_digest(stored, hashed):
                # Consume the code — one shot.
                cred.backup_codes_hashes = [
                    h for h in cred.backup_codes_hashes if h != stored
                ]
                return True
        return False
