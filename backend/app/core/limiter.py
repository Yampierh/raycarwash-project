# app/core/limiter.py
#
# Shared slowapi Limiter instance attached to app.state in main.py.
# Import from here in every router that needs rate limiting.
# Request MUST be the first parameter of any rate-limited handler.
#
# Key-function helpers cover the three buckets the contract plans
# (Plans 19/20/21) require:
#
#   - `get_remote_address` (slowapi default)   → per-IP (public endpoints)
#   - `user_or_ip_key`                         → per-user when authenticated
#                                                else per-IP (mixed routes)
#   - `user_required_key`                      → per-user only (auth-required)
#
# IMPORTANT — for per-user keys to work, the route must declare
# `Depends(populate_state_user)` BEFORE the `@limiter.limit(...)` wrapper
# fires. The decorator reads `request.state.user`, which FastAPI's auth
# dep does NOT populate by itself — it returns the User as a function
# parameter. `populate_state_user` is a thin wrapper around
# `get_current_user` that ALSO writes `request.state.user`.
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from domains.auth.service import get_current_user

if TYPE_CHECKING:
    from domains.users.models import User


def user_or_ip_key(request: Request) -> str:
    """Per-user when `request.state.user` is set, else per-IP.

    Use for routes that mix authenticated and anonymous traffic but want
    each authenticated user counted independently.
    """
    user = getattr(request.state, "user", None)
    user_id = getattr(user, "id", None)
    if user_id is not None:
        return f"user:{user_id}"
    return get_remote_address(request)


def user_required_key(request: Request) -> str:
    """Per-user only. Falls back to a clearly-marked IP key if no user
    is present so unauthenticated callers can never share a slot with
    authenticated ones (defensive — should not happen on
    `Depends(populate_state_user)` routes).
    """
    user = getattr(request.state, "user", None)
    user_id = getattr(user, "id", None)
    if user_id is not None:
        return f"user:{user_id}"
    return f"unauth-ip:{get_remote_address(request)}"


async def populate_state_user(
    request: Request,
    current_user: "User" = Depends(get_current_user),
) -> "User":
    """FastAPI dep that resolves the current user AND writes it to
    `request.state.user` so per-user rate-limit key functions can read it.

    Use this dep INSTEAD of `Depends(get_current_user)` on any route that
    declares `@limiter.limit(..., key_func=user_or_ip_key)` or
    `key_func=user_required_key`. The route handler body can still use
    the returned `current_user` exactly as before.
    """
    request.state.user = current_user
    return current_user


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],   # global safety net
    # TODO(infra): set `storage_uri=settings.REDIS_URL` (with the
    # `slowapi[redis]` extra) before multi-worker deployment so rate
    # limits are shared across uvicorn workers. The default MemoryStorage
    # is per-process; in a 4-worker cluster a client effectively gets
    # 4× the documented quota.
)
