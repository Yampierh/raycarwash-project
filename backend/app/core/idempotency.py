"""
app/core/idempotency.py — Idempotency-Key middleware + post-auth dep.

When a client sends `Idempotency-Key: <client-uuid>` on POST/PATCH/DELETE/PUT,
the first response is cached in Redis for 24h under one of two keys:

Legacy (still active for un-migrated routes):
    `idempotency:{user_id_or_anon}:{method}:{path}:{key}:{body_hash}`

V2 — H1 fix for routes that opt in via `Depends(resolve_idempotency)`:
    `idemp:v2:{user_id}:{method}:{path}:{key}:{body_hash}`

Subsequent identical requests (same user, same method+path, same key, AND
same body bytes) replay the cached response without re-executing the
handler. This protects against duplicate operations from double-taps or
network retries on flows like:
- Stripe SetupIntent
- /email/change-request
- /account/deletion-request
- Track 2/3 financial mutations (cash-out, cancel, etc.)

**Body binding (hotfix H2)** — both legacy and v2 keys include a SHA-256
prefix of the request body. Without this, two requests sharing an
Idempotency-Key but carrying different payloads would collide.

**User binding (H1 fix, Plan 22 §6.1.3)** — legacy key reads
`request.state.user`, but FastAPI auth deps run AFTER middleware so the
user_id falls back to `"anon"`. Empty-body mutations (PUT accept/decline)
all hash to `body_hash="empty"`, allowing cross-user collisions on
identical keys.

The v2 path moves the cache lookup into a post-auth FastAPI dependency
(`resolve_idempotency`) so `current_user.id` is available before the key
is built. Cache hits raise `_IdempotentReplay` which the registered
exception handler converts back to the cached Response with header
`X-Idempotent-Replay: true`. Cache misses register the resolved v2 key
on `request.state.idempotency_v2_cache_key` for the middleware's
response-write step to populate.

Per ADR-007 the envelope is declared explicitly on each endpoint, so the cached
body is a string and we return it verbatim with the original status code.
"""
from __future__ import annotations

import hashlib
import logging
from typing import TYPE_CHECKING, Awaitable, Callable

from fastapi import Depends, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from domains.auth.service import get_current_user

if TYPE_CHECKING:
    from domains.users.models import User

logger = logging.getLogger(__name__)

_IDEMPOTENT_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
_TTL_SECONDS = 24 * 60 * 60  # 24h
_MAX_BODY_BYTES = 256 * 1024  # 256 KB cap — bigger responses won't be cached
# 16 hex chars (8 bytes) of SHA-256 — collision-resistant enough for this use
# case (cache is per-user-per-endpoint-per-key already; this just guards
# against body mismatch within that already-narrow scope) and short enough
# to keep cache keys readable in `redis-cli MONITOR`.
_BODY_HASH_HEX_LEN = 16


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Replays cached responses when `Idempotency-Key` header is present and
    a matching cache entry exists. Reads Redis from `request.app.state.redis`.

    Falls open (no caching) if Redis is unavailable — the request still executes.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method not in _IDEMPOTENT_METHODS:
            return await call_next(request)

        key = request.headers.get("Idempotency-Key")
        if not key:
            return await call_next(request)

        # Read the body so we can hash it AND re-attach it for downstream
        # handlers. Starlette consumes the receive channel on first read, so
        # we replace request._receive with a one-shot that hands the bytes
        # back. Without this, every handler downstream would see an empty
        # body — a silent break worse than the bug we're fixing.
        body_bytes = await request.body()
        body_hash = (
            hashlib.sha256(body_bytes).hexdigest()[:_BODY_HASH_HEX_LEN]
            if body_bytes
            else "empty"
        )

        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]

        # Expose body_hash on state so the v2 post-auth dep
        # (`resolve_idempotency`) can build the user-scoped cache key
        # without re-reading the body. The dep is the SOLE owner of
        # cache lookup/write now — see module docstring + Plan 22 §6.1.3.
        request.state.idempotency_body_hash = body_hash

        # Execute handler (auth deps + resolve_idempotency dep + route).
        # If the dep finds a v2 cache hit it raises _IdempotentReplay,
        # which the registered exception handler turns into the cached
        # Response with `X-Idempotent-Replay: true`.
        response = await call_next(request)

        # On 2xx, if the dep registered a v2 cache key (i.e. the route
        # opted into idempotency), mirror the response there. The legacy
        # cross-user `idempotency:anon:...` write path was REMOVED with
        # the H1 fix; routes that don't use `resolve_idempotency` get
        # only body capture + receive replay, no cache replay.
        if not (200 <= response.status_code < 300):
            return response

        v2_cache_key = getattr(request.state, "idempotency_v2_cache_key", None)
        if not v2_cache_key:
            return response

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            return response

        body_bytes_out = b""
        async for chunk in response.body_iterator:
            body_bytes_out += chunk
        rebuilt = StarletteResponse(
            content=body_bytes_out,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

        if len(body_bytes_out) <= _MAX_BODY_BYTES:
            try:
                await redis.hset(v2_cache_key, mapping={
                    "status": str(response.status_code),
                    "body": body_bytes_out.decode("utf-8", errors="replace"),
                    "content_type": response.headers.get("content-type", "application/json"),
                })
                await redis.expire(v2_cache_key, _TTL_SECONDS)
            except Exception as exc:
                logger.warning("Idempotency v2 cache write failed (%s)", exc)

        return rebuilt


# ---------------------------------------------------------------------------
# V2 path — H1 fix (Plan 22 §6.1.3). Opt-in via `Depends(resolve_idempotency)`.
# ---------------------------------------------------------------------------


class _IdempotentReplay(Exception):
    """Raised by `resolve_idempotency` on cache hit. Registered FastAPI
    exception handler converts this into the cached Response with header
    `X-Idempotent-Replay: true`. Must NOT be caught by user code.
    """

    def __init__(self, status_code: int, body: bytes, content_type: str) -> None:
        self.status_code = status_code
        self.body = body
        self.content_type = content_type


def build_idempotency_v2_cache_key(
    user_id: str, method: str, path: str, idempotency_key: str, body_hash: str,
) -> str:
    return (
        f"idemp:v2:{user_id}:{method}:{path}:{idempotency_key}:{body_hash}"
    )


async def _resolve_idempotency_impl(request: Request, user: "User") -> None:
    """Pure impl — separated from the FastAPI dep so tests can call it
    without going through `Depends(get_current_user)`."""
    idem_key = request.headers.get("Idempotency-Key")
    if not idem_key:
        return

    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        return

    body_hash = getattr(request.state, "idempotency_body_hash", "empty")
    cache_key = build_idempotency_v2_cache_key(
        user_id=str(user.id),
        method=request.method,
        path=request.url.path,
        idempotency_key=idem_key,
        body_hash=body_hash,
    )

    try:
        cached = await redis.hgetall(cache_key)
    except Exception as exc:
        logger.warning("Idempotency v2 read failed (%s) — proceeding without cache", exc)
        return

    if cached:
        try:
            status_code = int(cached.get("status", 200))
            body = cached.get("body", "").encode("utf-8")
            content_type = cached.get("content_type", "application/json")
        except Exception as exc:
            logger.warning("Idempotency v2 cached payload corrupt (%s) — re-executing", exc)
        else:
            raise _IdempotentReplay(
                status_code=status_code, body=body, content_type=content_type,
            )

    request.state.idempotency_v2_cache_key = cache_key


async def resolve_idempotency(
    request: Request,
    current_user: "User" = Depends(get_current_user),
) -> None:
    """
    Post-auth FastAPI dependency that fixes H1 for routes that opt in.

    Usage in a route:

        from app.core.idempotency import resolve_idempotency

        @router.post("/detailers/me/earnings/cash-out")
        async def cash_out(
            body: CashOutRequest,
            current_user: User = Depends(require_role("detailer")),
            _idem: None = Depends(resolve_idempotency),
        ):
            ...

    FastAPI deduplicates `Depends(get_current_user)` by callable identity,
    so even when the route also declares `require_role("detailer")`
    (which itself depends on `get_current_user`), the JWT decode runs once.

    Behaviour:
      - No `Idempotency-Key` header → no-op.
      - No Redis configured → no-op (fail-open, matches legacy).
      - Cache hit → raises `_IdempotentReplay` which the exception handler
        converts into the cached Response with `X-Idempotent-Replay: true`.
      - Cache miss → writes the resolved v2 cache key to
        `request.state.idempotency_v2_cache_key` so the middleware
        response-write step populates it on 2xx.
    """
    await _resolve_idempotency_impl(request, current_user)
