"""
domains/auth/routers/sessions.py — Plan 23 Fase 2 + Fase 6.

Surfaces the stateful Session table built in Fase 1 to the user:

  - GET    /auth/sessions                    — list active sessions
  - POST   /auth/sessions/{session_id}/revoke — revoke a specific session
  - DELETE /auth/sessions                    — revoke everything (log out everywhere)
  - DELETE /auth/sessions/{family_id}        — legacy by-family revoke (back-compat)

The current request's session is flagged with `is_current=True` (decoded
from the `sid` claim on the incoming access token) so the frontend can
disable the "Revoke" button on it.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.refresh_token_repository import RefreshTokenRepository
from domains.auth.schemas import (
    SessionRead, SessionRevokeResponse, SessionsListResponse,
)
from domains.auth.service import (
    AuthService, get_current_user, invalidate_session_cache,
)
from domains.auth.session_repository import SessionRepository
from domains.users.models import User
from infrastructure.db.session import get_db
from infrastructure.redis.client import get_redis


router = APIRouter(prefix="/auth", tags=["Authentication"])


def _current_sid_from_header(authorization: str | None) -> uuid.UUID | None:
    """Pull the `sid` claim off the current request's access token. Used
    purely for the `is_current` UX flag — returning None is fine."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    raw = authorization.split(" ", 1)[1].strip()
    if not raw:
        return None
    try:
        payload = AuthService.decode_token(raw, expected_type="access")
    except Exception:
        return None
    sid_str = payload.get("sid")
    if not sid_str:
        return None
    try:
        return uuid.UUID(sid_str)
    except ValueError:
        return None


def _session_to_read(session, *, is_current: bool) -> SessionRead:
    return SessionRead(
        id=session.id,
        family_id=session.family_id,
        device_name=session.device_name,
        device_type=session.device_type,
        ip_address=session.ip_address,
        ip_country=session.ip_country,
        ip_city=session.ip_city,
        user_agent=session.user_agent,
        created_at=session.created_at,
        last_active_at=session.last_active_at,
        revoked=session.revoked,
        is_current=is_current,
        # Back-compat alias for callers still on the pre-Fase-2 shape.
        last_used_at=session.last_active_at,
    )


@router.get(
    "/sessions",
    response_model=SessionsListResponse,
    summary="List active sessions for current user",
)
async def list_sessions(
    authorization: str | None = Header(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionsListResponse:
    """Rich per-device list backed by the `sessions` table (Plan 23 F1).
    Pre-Fase-2 callers receive a superset shape — the old `family_id` /
    `last_used_at` fields are still populated."""
    sessions, total = await SessionRepository(db).list_for_user(
        current_user.id, limit=50, offset=0, include_revoked=False,
    )
    current_sid = _current_sid_from_header(authorization)
    payload = [
        _session_to_read(s, is_current=(current_sid is not None and s.id == current_sid))
        for s in sessions
    ]
    return SessionsListResponse(sessions=payload, total=total)


@router.post(
    "/sessions/{session_id}/revoke",
    response_model=SessionRevokeResponse,
    summary="Revoke a specific session by id (Plan 23 Fase 6 UX endpoint)",
)
async def revoke_session_by_id(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> SessionRevokeResponse:
    """UX-facing revoke. Validates ownership, revokes the Session row,
    tears down the matching refresh-token family, and evicts the Redis
    cache so the next request sees the new state immediately."""
    repo = SessionRepository(db)
    session = await repo.get_by_id(session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    revoked = await repo.revoke(session_id)
    if not revoked:
        return SessionRevokeResponse(
            revoked_session_id=session_id,
            revoked_family_id=session.family_id,
            message="Session was already revoked.",
        )

    await RefreshTokenRepository(db).revoke_family(session.family_id)
    await db.commit()
    await invalidate_session_cache(str(session_id), redis)

    return SessionRevokeResponse(
        revoked_session_id=session_id,
        revoked_family_id=session.family_id,
        message="Session revoked successfully.",
    )


@router.delete(
    "/sessions/{family_id}",
    response_model=SessionRevokeResponse,
    summary="Revoke a specific session (legacy by family_id, back-compat)",
)
async def revoke_session_legacy(
    family_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
) -> SessionRevokeResponse:
    """Pre-Fase-2 callers passed `family_id`. We resolve it to the
    matching Session row, then delegate to the same code path as the
    by-id revoke."""
    session = await SessionRepository(db).get_by_family(family_id)
    if session is None or session.user_id != current_user.id:
        # Tokens minted pre-rollout may not have a Session row yet —
        # fall back to the old refresh-token-family revoke so users on
        # legacy tokens can still log out a specific device.
        rt_repo = RefreshTokenRepository(db)
        legacy = await rt_repo.get_session_by_family(current_user.id, family_id)
        if legacy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        await rt_repo.revoke_session(current_user.id, family_id)
        await db.commit()
        return SessionRevokeResponse(
            revoked_session_id=family_id,
            revoked_family_id=family_id,
            message="Legacy session revoked successfully.",
        )

    repo = SessionRepository(db)
    await repo.revoke(session.id)
    await RefreshTokenRepository(db).revoke_family(family_id)
    await db.commit()
    await invalidate_session_cache(str(session.id), redis)

    return SessionRevokeResponse(
        revoked_session_id=session.id,
        revoked_family_id=family_id,
        message="Session revoked successfully.",
    )


@router.delete(
    "/sessions",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Revoke all sessions (log out everywhere)",
)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke every active session for the current user. Cache TTL bounds
    the blast radius: any cached `revoked=False` row expires within
    AUTH_SESSION_CACHE_TTL_SECONDS, after which the DB read returns
    `revoked=True` and subsequent requests 401."""
    await SessionRepository(db).revoke_all_for_user(current_user.id)
    await RefreshTokenRepository(db).revoke_all_for_user(current_user.id)
    await db.commit()
