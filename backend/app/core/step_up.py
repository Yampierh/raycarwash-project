"""
app/core/step_up.py — Step-up authentication dependency (ADR-004).

Sensitive operations and `?include=security|sessions` on the Profile Hub
require recent re-authentication (≤ 5 min). We check two layers:

  1. Redis primary: key `auth:stepup:{user_id}` = last_auth_at ISO timestamp,
     TTL aligned with STEP_UP_TTL_MINUTES. Updated on every successful auth event.
  2. DB fallback: column `User.last_step_up_at`. Survives Redis outages.

If neither is recent → raise StepUpRequiredError, which translates to
401 + WWW-Authenticate: StepUp + body `{error: {code: "step_up_required"}}`.

Call `mark_step_up()` from AuthService after a successful authenticate_user(),
OAuth verify, passkey verify, or password verify.

Profile Hub usage (`?include=security`) calls `is_step_up_recent()` directly
to decide between 401, 200 with skipped blocks, or normal serve.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from domains.users.models import User
from infrastructure.db.session import get_db

logger = logging.getLogger(__name__)

_REDIS_KEY_PREFIX = "auth:stepup:"


def _step_up_window() -> timedelta:
    return timedelta(minutes=get_settings().STEP_UP_TTL_MINUTES)


def _redis_key(user_id: UUID | str) -> str:
    return f"{_REDIS_KEY_PREFIX}{user_id}"


class StepUpRequiredError(HTTPException):
    """Raised when a sensitive operation needs recent re-auth. Translated to 401."""

    def __init__(self, requires: list[str] | None = None):
        detail = {
            "code": "step_up_required",
            "message": "Recent re-authentication required for this operation.",
            "requires_step_up": requires or [],
        }
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        self.requires_step_up = requires or []
        self.headers = {"WWW-Authenticate": 'StepUp realm="raycarwash"'}


async def mark_step_up(
    request: Request,
    user: User,
    db: AsyncSession,
) -> None:
    """
    Record a fresh authentication event. Updates Redis (primary) and DB (fallback).
    Call from AuthService on any successful auth (login, password verify, OAuth, passkey).
    """
    now = datetime.now(timezone.utc)
    ttl_seconds = int(_step_up_window().total_seconds())

    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        try:
            await redis.set(_redis_key(user.id), now.isoformat(), ex=ttl_seconds)
        except Exception as exc:
            logger.warning("step_up: Redis write failed (%s) — DB fallback only", exc)

    user.last_step_up_at = now
    await db.flush()


async def is_step_up_recent(request: Request, user: User) -> bool:
    """
    Non-raising check used by Profile Hub when handling `?include=security` and
    deciding between 401, ?on_step_up=skip behavior, or normal serve.
    """
    threshold = datetime.now(timezone.utc) - _step_up_window()

    # 1. Redis primary
    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        try:
            cached = await redis.get(_redis_key(user.id))
            if cached:
                ts = datetime.fromisoformat(cached) if isinstance(cached, str) else None
                if ts and ts > threshold:
                    return True
        except Exception as exc:
            logger.warning("step_up: Redis read failed (%s) — falling back to DB", exc)

    # 2. DB fallback
    if user.last_step_up_at and user.last_step_up_at > threshold:
        return True

    return False


from fastapi import Depends

# Local imports — verified no circular reference: auth.service doesn't
# import step_up, and step_up was historically imported before
# auth.service in the legacy main.py, so we can safely reach into it.
from domains.auth.service import get_current_user


async def require_step_up(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency for endpoints that need recent re-auth (≤
    STEP_UP_TTL_MINUTES).

    Resolves the authenticated user via `get_current_user`, then checks
    Redis (primary) + `User.last_step_up_at` (fallback). Raises
    `StepUpRequiredError` (401 `step_up_required`) if neither layer
    shows a recent auth event.

    Usage:
        @router.post("/sensitive")
        async def handler(user = Depends(require_step_up)):
            ...
    """
    request.state.user = current_user
    if not await is_step_up_recent(request, current_user):
        raise StepUpRequiredError()
    return current_user
