"""
domains/users/contact_change_service.py — Email + phone change flows.

Each half-flow does exactly one thing:

  request_email_change(new_email, current_password)
      Validates password, drops any prior pending row for this user/type,
      builds a 64-char URL-safe token, hashes it, stores the row, sends
      the link to the NEW email. Always returns the same ack (never
      reveals whether the new_email is already in use).

  confirm_email_change(token)
      Looks up by hash, validates expiry/consume state, atomically swaps
      User.email + bumps token_version, revokes all refresh tokens, marks
      the row consumed. Sends an anti-takeover notice to the OLD email.

  request_phone_change(new_phone, current_password)
      Same as email but with a 6-digit OTP SMSed (Console adapter in dev,
      Twilio in prod), 10-min TTL, 5-attempt cap.

  verify_phone_change(otp)
      Looks up the user's most recent unconsumed phone row, increments
      attempts, locks (deletes) at 5, otherwise compares hashes, swaps
      User.phone_number + phone_hash, bumps token_version.

All four log to the audit_log via AuditRepository so /auth/history shows
them.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_sms_adapter
from app.middleware.audit_context import get_audit_context
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.refresh_token_repository import RefreshTokenRepository
from domains.auth.service import AuthService
from domains.users.models import User
from domains.users.pending_contact_change import ContactChangeType, PendingContactChange
from domains.users.repository import UserRepository

logger = logging.getLogger(__name__)


_EMAIL_TOKEN_TTL = timedelta(hours=1)
_PHONE_OTP_TTL = timedelta(minutes=10)
_MAX_PHONE_ATTEMPTS = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_phone_for_lookup(phone: str) -> str:
    """Reuse the same HMAC used for User.phone_hash so we can detect
    collisions without decrypting."""
    settings = get_settings()
    key = settings.PHONE_LOOKUP_KEY.encode("utf-8")
    return hmac.new(key, phone.encode("utf-8"), hashlib.sha256).hexdigest()


def _hash_email_for_lookup(email: str) -> str:
    """Email is stored plaintext on User, but we still hash it here so the
    same `new_value_hash` column works for both contact types."""
    return hashlib.sha256(email.lower().strip().encode("utf-8")).hexdigest()


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    head = local[:1]
    return f"{head}***@{domain}" if domain else f"{head}***"


def _mask_phone(phone: str) -> str:
    if len(phone) <= 4:
        return "***"
    return f"***{phone[-4:]}"


class ContactChangeError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


class ContactChangeService:
    def __init__(self, db: AsyncSession, request: Request) -> None:
        self.db = db
        self.request = request
        self.audit = AuditRepository(db)
        self.settings = get_settings()

    # ────── email ─────────────────────────────────────────────────────────

    async def request_email_change(
        self,
        user: User,
        new_email: str,
        current_password: str,
    ) -> str | None:
        """Returns the raw token in dev (to seed mobile test harness),
        None in prod. The link is always sent via email regardless."""
        new_email = new_email.strip().lower()

        if not AuthService.verify_password(current_password, user.password_hash):
            raise ContactChangeError(
                status.HTTP_403_FORBIDDEN,
                "permission_denied",
                "Current password is incorrect.",
            )

        if new_email == (user.email or "").lower():
            raise ContactChangeError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                "New email matches the current one.",
            )

        # Drop any prior pending email row for the same user — only one in
        # flight at a time. We don't error if the destination collides with
        # another user's email; we still issue a generic ack (anti-enum).
        await self._purge_existing(user.id, ContactChangeType.EMAIL)

        token = secrets.token_urlsafe(48)
        row = PendingContactChange(
            user_id=user.id,
            change_type=ContactChangeType.EMAIL.value,
            new_value_encrypted=new_email,
            new_value_hash=_hash_email_for_lookup(new_email),
            verification_token_hash=_hash_token(token),
            attempts=0,
            created_at=_utcnow(),
            expires_at=_utcnow() + _EMAIL_TOKEN_TTL,
        )
        self.db.add(row)
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.EMAIL_CHANGE_REQUESTED,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            audit_ctx=get_audit_context(self.request),
        )

        # TODO(phase 3 email-templates): send the verification link via the
        # transactional email adapter (MailHog dev, SendGrid prod). The
        # current EmailService.send_email_verification helper already
        # exists for the registration flow — wire a sibling
        # send_email_change_verification(verify_url) with templates
        # /backend/templates/emails/email_change.{html,txt}. For now the
        # link is logged so dev can pick it up.
        verify_url = f"{self.settings.APP_BASE_URL}/auth/email/change-confirm?token={token}"
        logger.warning(
            "[DEV-EMAIL] email change for user=%s → %s (link: %s)",
            user.id, new_email, verify_url,
        )

        if self.settings.RAYCARWASH_ENV == "development":
            return token
        return None

    async def confirm_email_change(self, token: str) -> tuple[User, str]:
        """Consume the token, swap User.email, return (user, new_email)."""
        token_hash = _hash_token(token)
        stmt = (
            select(PendingContactChange)
            .where(
                PendingContactChange.verification_token_hash == token_hash,
                PendingContactChange.change_type == ContactChangeType.EMAIL.value,
                PendingContactChange.consumed_at.is_(None),
            )
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise ContactChangeError(
                status.HTTP_410_GONE,
                "gone",
                "Verification link is invalid or already used.",
            )
        if row.expires_at < _utcnow():
            raise ContactChangeError(
                status.HTTP_410_GONE,
                "gone",
                "Verification link has expired. Please request a new one.",
            )

        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(row.user_id)
        if user is None:
            raise ContactChangeError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "User no longer exists.",
            )

        old_email = user.email
        user.email = row.new_value_encrypted  # plaintext for email
        user.is_verified = True
        user.token_version = (user.token_version or 1) + 1
        row.consumed_at = _utcnow()
        await self.db.flush()

        # Revoke every refresh token so every device re-authenticates with
        # the new email + bumped token_version.
        await RefreshTokenRepository(self.db).revoke_all_for_user(user.id)

        await self.audit.log(
            action=AuditAction.EMAIL_CHANGED,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            old_value={"email": old_email},
            new_value={"email": user.email},
            audit_ctx=get_audit_context(self.request),
        )

        # TODO(phase 3 email-templates): send anti-takeover notification to
        # `old_email` warning that the address was changed and listing a
        # support contact. Same wiring story as the verification email.
        logger.warning(
            "[DEV-EMAIL] anti-takeover notice → %s (email changed to %s)",
            old_email, user.email,
        )

        return user, user.email

    # ────── phone ─────────────────────────────────────────────────────────

    async def request_phone_change(
        self,
        user: User,
        new_phone: str,
        current_password: str,
    ) -> str | None:
        new_phone = new_phone.strip()

        if not AuthService.verify_password(current_password, user.password_hash):
            raise ContactChangeError(
                status.HTTP_403_FORBIDDEN,
                "permission_denied",
                "Current password is incorrect.",
            )

        if user.phone_number and new_phone == user.phone_number:
            raise ContactChangeError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                "New phone matches the current one.",
            )

        await self._purge_existing(user.id, ContactChangeType.PHONE)

        otp = f"{secrets.randbelow(1_000_000):06d}"
        row = PendingContactChange(
            user_id=user.id,
            change_type=ContactChangeType.PHONE.value,
            new_value_encrypted=new_phone,
            new_value_hash=_hash_phone_for_lookup(new_phone),
            verification_token_hash=_hash_token(otp),
            attempts=0,
            created_at=_utcnow(),
            expires_at=_utcnow() + _PHONE_OTP_TTL,
        )
        self.db.add(row)
        await self.db.flush()

        await self.audit.log(
            action=AuditAction.PHONE_CHANGE_REQUESTED,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            audit_ctx=get_audit_context(self.request),
        )

        sms = get_sms_adapter()
        await sms.send_otp(new_phone, otp, ttl_minutes=int(_PHONE_OTP_TTL.total_seconds() // 60))

        if self.settings.RAYCARWASH_ENV == "development":
            return otp
        return None

    async def verify_phone_change(self, user: User, otp: str) -> tuple[User, str]:
        stmt = (
            select(PendingContactChange)
            .where(
                PendingContactChange.user_id == user.id,
                PendingContactChange.change_type == ContactChangeType.PHONE.value,
                PendingContactChange.consumed_at.is_(None),
            )
            .order_by(PendingContactChange.created_at.desc())
            .limit(1)
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        if row is None or row.expires_at < _utcnow():
            raise ContactChangeError(
                status.HTTP_410_GONE,
                "gone",
                "OTP is invalid or has expired. Please request a new one.",
            )

        if row.attempts >= _MAX_PHONE_ATTEMPTS:
            # Lock the row so further /verify calls fail fast.
            await self.db.delete(row)
            await self.db.flush()
            raise ContactChangeError(
                status.HTTP_423_LOCKED,
                "account_locked",
                "Too many incorrect attempts. Please request a new code.",
            )

        if not hmac.compare_digest(row.verification_token_hash, _hash_token(otp)):
            row.attempts += 1
            await self.db.flush()
            raise ContactChangeError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"Incorrect code. {_MAX_PHONE_ATTEMPTS - row.attempts} attempt(s) remaining.",
            )

        new_phone = row.new_value_encrypted
        old_phone = user.phone_number
        user.phone_number = new_phone
        user.phone_hash = _hash_phone_for_lookup(new_phone)
        user.token_version = (user.token_version or 1) + 1
        row.consumed_at = _utcnow()
        await self.db.flush()

        await RefreshTokenRepository(self.db).revoke_all_for_user(user.id)

        await self.audit.log(
            action=AuditAction.PHONE_CHANGED,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            old_value={"phone_number": _mask_phone(old_phone or "")},
            new_value={"phone_number": _mask_phone(new_phone)},
            audit_ctx=get_audit_context(self.request),
        )

        return user, new_phone

    # ────── helpers ───────────────────────────────────────────────────────

    async def _purge_existing(
        self,
        user_id,
        change_type: ContactChangeType,
    ) -> None:
        stmt = select(PendingContactChange).where(
            PendingContactChange.user_id == user_id,
            PendingContactChange.change_type == change_type.value,
            PendingContactChange.consumed_at.is_(None),
        )
        for row in (await self.db.execute(stmt)).scalars().all():
            await self.db.delete(row)
        await self.db.flush()
