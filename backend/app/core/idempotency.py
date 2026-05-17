"""
app/core/idempotency.py — Idempotency-Key middleware for sensitive mutations.

When a client sends `Idempotency-Key: <client-uuid>` on POST/PATCH/DELETE/PUT,
the first response is cached in Redis for 24h under key:
    `idempotency:{user_id_or_anon}:{method}:{path}:{key}:{body_hash}`

Subsequent identical requests (same user, same method+path, same key, AND
same body bytes) replay the cached response without re-executing the
handler. This protects against duplicate operations from double-taps or
network retries on flows like:
- Stripe SetupIntent
- /email/change-request
- /account/deletion-request

**Body binding (hotfix H2)** — the cache key includes a SHA-256 prefix of
the request body. Without this, two requests sharing an Idempotency-Key
but carrying different payloads would collide and the second caller
would receive the first caller's response — a real hazard on payments
where a client retries with a corrected amount. Different body = different
operation = different cache slot.

Per ADR-007 the envelope is declared explicitly on each endpoint, so the cached
body is a string and we return it verbatim with the original status code.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

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

        redis = getattr(request.app.state, "redis", None)
        if redis is None:
            logger.debug("Idempotency middleware: Redis not configured, skipping cache")
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

        cache_key = self._build_cache_key(request, key, body_hash)

        # 1. Try to serve cached response
        try:
            cached = await redis.hgetall(cache_key)
        except Exception as exc:
            logger.warning("Idempotency middleware: Redis read failed (%s), skipping cache", exc)
            return await call_next(request)

        if cached:
            try:
                status_code = int(cached.get("status", 200))
                body = cached.get("body", "").encode("utf-8")
                headers = {
                    "content-type": cached.get("content_type", "application/json"),
                    "X-Idempotent-Replay": "true",
                }
                return StarletteResponse(
                    content=body,
                    status_code=status_code,
                    headers=headers,
                )
            except Exception as exc:
                logger.warning("Idempotency middleware: cached payload corrupt (%s), re-executing", exc)

        # 2. Execute handler
        response = await call_next(request)

        # 3. Cache successful responses only (2xx). 4xx/5xx not cached so retries can recover.
        if 200 <= response.status_code < 300:
            body_bytes = b""
            async for chunk in response.body_iterator:
                body_bytes += chunk
            response = StarletteResponse(
                content=body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
            if len(body_bytes) <= _MAX_BODY_BYTES:
                try:
                    await redis.hset(cache_key, mapping={
                        "status": str(response.status_code),
                        "body": body_bytes.decode("utf-8", errors="replace"),
                        "content_type": response.headers.get("content-type", "application/json"),
                    })
                    await redis.expire(cache_key, _TTL_SECONDS)
                except Exception as exc:
                    logger.warning("Idempotency middleware: Redis write failed (%s)", exc)

        return response

    @staticmethod
    def _build_cache_key(
        request: Request, idempotency_key: str, body_hash: str
    ) -> str:
        user = getattr(request.state, "user", None)
        user_id = str(getattr(user, "id", "anon")) if user else "anon"
        return (
            f"idempotency:{user_id}:{request.method}:{request.url.path}:"
            f"{idempotency_key}:{body_hash}"
        )
