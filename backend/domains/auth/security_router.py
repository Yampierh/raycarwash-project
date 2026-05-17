"""
domains/auth/security_router.py — Security center endpoints under /api/v1/auth.

Per ADR-001 these live in the auth domain (identity + credentials), not
under /users/me. The Profile Hub re-exposes the relevant blocks via
`?include=security,sessions` for the SecurityScreen UI.

  GET    /auth/security              summary (no step-up)
  GET    /auth/history               unified login + audit feed
  POST   /auth/two-fa/enroll         step-up
  POST   /auth/two-fa/verify         auth (no step-up — IS the step-up)
  DELETE /auth/two-fa                step-up
  POST   /auth/two-fa/backup-codes/regenerate   step-up
  GET    /auth/passkeys              auth (list)
  PATCH  /auth/passkeys/{id}         auth (rename device_name)
  DELETE /auth/passkeys/{id}         step-up
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import Depends, Query, Request, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.core.step_up import is_step_up_recent, require_step_up
from app.exception_handlers import BusinessError
from domains.audit.models import AuditAction, AuditLog
from domains.auth.models import (
    AuthProvider,
    RefreshToken,
    UserLoginHistory,
    WebAuthnCredential,
)
from domains.auth.service import AuthService, get_current_user
from domains.auth.totp_credential import TotpCredential
from domains.auth.totp_service import TotpService
from domains.auth.security_schemas import (
    PasskeyRenameRequest,
    PasskeySummary,
    SecurityHistoryItem,
    SecuritySummaryResponse,
    TotpBackupCodesResponse,
    TotpEnrollResponse,
    TotpVerifyRequest,
)
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope, Meta, PaginatedEnvelope

logger = logging.getLogger(__name__)

router = EnvelopeRouter(prefix="/api/v1/auth", tags=["Auth · Security"])


# ─── /auth/security ───────────────────────────────────────────────────────────


@router.get(
    "/security",
    response_model=Envelope[SecuritySummaryResponse],
    summary="Consolidated security summary (Hub-equivalent of include=security).",
)
async def get_security_summary(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[SecuritySummaryResponse]:
    request.state.user = current_user

    passkeys_count = (
        await db.scalar(
            select(func.count()).select_from(WebAuthnCredential).where(
                WebAuthnCredential.user_id == current_user.id,
            )
        )
    ) or 0
    sessions_count = (
        await db.scalar(
            select(func.count()).select_from(RefreshToken).where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked.is_(False),
            )
        )
    ) or 0
    last_login_at = await db.scalar(
        select(func.max(UserLoginHistory.login_at)).where(
            UserLoginHistory.user_id == current_user.id,
            UserLoginHistory.was_successful.is_(True),
        )
    )
    recent_failed = (
        await db.scalar(
            select(func.count()).select_from(UserLoginHistory).where(
                UserLoginHistory.user_id == current_user.id,
                UserLoginHistory.was_successful.is_(False),
            )
        )
    ) or 0
    totp_row = await db.scalar(
        select(TotpCredential).where(TotpCredential.user_id == current_user.id)
    )
    last_pwd_change = await db.scalar(
        select(func.max(AuditLog.created_at)).where(
            AuditLog.actor_id == current_user.id,
            AuditLog.action == AuditAction.PASSWORD_CHANGED,
        )
    )

    return Envelope(data=SecuritySummaryResponse(
        has_password=bool(current_user.password_hash),
        two_factor_enabled=bool(totp_row and totp_row.enabled),
        passkeys_count=int(passkeys_count),
        last_password_change=last_pwd_change,
        last_login_at=last_login_at,
        step_up_recent=await is_step_up_recent(request, current_user),
        active_sessions_count=int(sessions_count),
        recent_failed_attempts=int(recent_failed),
    ))


# ─── /auth/history ────────────────────────────────────────────────────────────


# Audit actions surfaced under /auth/history. Anything that should appear
# in the Profile Hub's `/users/me/profile-changes` feed goes there instead.
_SECURITY_ACTIONS = {
    AuditAction.PASSWORD_CHANGED,
    AuditAction.PASSWORD_RESET_REQUESTED,
    AuditAction.EMAIL_CHANGE_REQUESTED,
    AuditAction.EMAIL_CHANGED,
    AuditAction.PHONE_CHANGE_REQUESTED,
    AuditAction.PHONE_CHANGED,
    AuditAction.TWO_FA_ENABLED,
    AuditAction.TWO_FA_DISABLED,
    AuditAction.PASSKEY_REGISTERED,
    AuditAction.PASSKEY_REVOKED,
    AuditAction.SESSION_REVOKED,
    AuditAction.ALL_SESSIONS_REVOKED,
    AuditAction.USER_LOGIN,
    AuditAction.USER_SOCIAL_LOGIN,
}


@router.get(
    "/history",
    response_model=PaginatedEnvelope[SecurityHistoryItem],
    summary="Unified security event feed: logins + security-related audit log entries.",
)
async def get_security_history(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedEnvelope[SecurityHistoryItem]:
    request.state.user = current_user

    # Pull recent rows from both sources; sort + slice in memory after the
    # union. Phase 8 will add proper cursor pagination using created_at +
    # id tuples — this Phase 3 version is bounded by `limit` only.
    login_rows = (
        await db.execute(
            select(UserLoginHistory)
            .where(UserLoginHistory.user_id == current_user.id)
            .order_by(desc(UserLoginHistory.login_at))
            .limit(limit)
        )
    ).scalars().all()

    audit_rows = (
        await db.execute(
            select(AuditLog)
            .where(
                AuditLog.actor_id == current_user.id,
                AuditLog.action.in_([a.value for a in _SECURITY_ACTIONS]),
            )
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
    ).scalars().all()

    items: list[SecurityHistoryItem] = []
    for row in login_rows:
        items.append(SecurityHistoryItem(
            id=row.id,
            type="login",
            occurred_at=row.login_at,
            summary=(
                f"Login from {row.device_name or 'unknown device'}"
                if row.was_successful
                else f"Failed login ({row.failure_reason or 'unknown'})"
            ),
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            device_name=row.device_name,
            was_successful=row.was_successful,
            failure_reason=row.failure_reason,
        ))
    for row in audit_rows:
        items.append(SecurityHistoryItem(
            id=row.id,
            type="audit",
            occurred_at=row.created_at,
            summary=row.action.replace("_", " ").title() if isinstance(row.action, str) else str(row.action),
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            details={
                "old_value": row.old_value,
                "new_value": row.new_value,
                "metadata": row.metadata_,
            },
        ))

    items.sort(key=lambda i: i.occurred_at, reverse=True)
    items = items[:limit]

    return PaginatedEnvelope[SecurityHistoryItem](
        data=items,
        meta=Meta(limit=limit, has_more=len(items) == limit),
    )


# ─── /auth/two-fa/* ───────────────────────────────────────────────────────────


@router.post(
    "/two-fa/enroll",
    response_model=Envelope[TotpEnrollResponse],
    summary="Begin TOTP enrollment. Returns the secret + QR + backup codes ONCE.",
)
async def two_fa_enroll(
    request: Request,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> Envelope[TotpEnrollResponse]:
    request.state.user = current_user
    payload = await TotpService(db, request).enroll(current_user)
    return Envelope(data=TotpEnrollResponse(**payload))


@router.post(
    "/two-fa/verify",
    response_model=Envelope[SecuritySummaryResponse],
    summary="Confirm enrollment with the first OTP. Flips two_factor_enabled=True.",
)
async def two_fa_verify(
    body: TotpVerifyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[SecuritySummaryResponse]:
    request.state.user = current_user
    await TotpService(db, request).verify(current_user, body.code)
    # Hotfix H3 — a successful TOTP code is a real auth factor (something
    # the user has). Bump the step-up window so the user can chain
    # follow-up actions (e.g. enroll a passkey) without re-prompting.
    await AuthService.record_step_up_success(request, current_user, db, auth_method="totp")
    # Re-fetch summary so the client sees the updated `two_factor_enabled`.
    return await get_security_summary(request, current_user, db)


@router.delete(
    "/two-fa",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Disable TOTP 2FA. Removes the credential row.",
)
async def two_fa_disable(
    request: Request,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> None:
    request.state.user = current_user
    await TotpService(db, request).disable(current_user)


@router.post(
    "/two-fa/backup-codes/regenerate",
    response_model=Envelope[TotpBackupCodesResponse],
    summary="Generate a fresh set of backup codes. Old codes are immediately invalid.",
)
async def two_fa_regenerate_backup_codes(
    request: Request,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> Envelope[TotpBackupCodesResponse]:
    request.state.user = current_user
    codes = await TotpService(db, request).regenerate_backup_codes(current_user)
    return Envelope(data=TotpBackupCodesResponse(backup_codes=codes))


# ─── /auth/passkeys (admin) ───────────────────────────────────────────────────


@router.get(
    "/passkeys",
    response_model=Envelope[list[PasskeySummary]],
    summary="List the user's registered passkeys.",
)
async def list_passkeys(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[PasskeySummary]]:
    request.state.user = current_user
    rows = (
        await db.execute(
            select(WebAuthnCredential)
            .where(WebAuthnCredential.user_id == current_user.id)
            .order_by(WebAuthnCredential.created_at.desc())
        )
    ).scalars().all()
    items = [
        PasskeySummary(
            id=r.id,
            device_name=getattr(r, "device_name", None),
            created_at=r.created_at,
            last_used_at=getattr(r, "last_used_at", None),
        )
        for r in rows
    ]
    return Envelope(data=items)


@router.patch(
    "/passkeys/{passkey_id}",
    response_model=Envelope[PasskeySummary],
    summary="Rename a passkey's device label.",
)
async def rename_passkey(
    passkey_id: uuid.UUID,
    body: PasskeyRenameRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[PasskeySummary]:
    request.state.user = current_user
    row = await db.scalar(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == passkey_id,
            WebAuthnCredential.user_id == current_user.id,
        )
    )
    if row is None:
        raise BusinessError(
            code="resource_not_found",
            message="Passkey not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if not hasattr(row, "device_name"):
        raise BusinessError(
            code="conflict",
            message="Passkey model does not support device_name in this schema version.",
            status_code=status.HTTP_409_CONFLICT,
        )
    row.device_name = body.device_name
    await db.flush()
    return Envelope(data=PasskeySummary(
        id=row.id,
        device_name=row.device_name,
        created_at=row.created_at,
        last_used_at=getattr(row, "last_used_at", None),
    ))


@router.delete(
    "/passkeys/{passkey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Revoke a passkey. Requires step-up.",
)
async def revoke_passkey(
    passkey_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> None:
    request.state.user = current_user
    row = await db.scalar(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == passkey_id,
            WebAuthnCredential.user_id == current_user.id,
        )
    )
    if row is None:
        raise BusinessError(
            code="resource_not_found",
            message="Passkey not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    await db.delete(row)
    await db.flush()
