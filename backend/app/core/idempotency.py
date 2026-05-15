"""
app/core/idempotency.py — Idempotency-Key middleware for sensitive mutations.

When a client sends `Idempotency-Key: <client-uuid>` on POST/PATCH/DELETE/PUT,
the first response is cached in Redis for 24h under key:
    `idempotency:{user_id_or_anon}:{method}:{path}:{key}`

Subsequent identical requests (same user, same method+path, same key) replay
the cached response without re-executing the handler. This protects against
duplicate operations from double-taps or network retries on flows like:
- Stripe SetupIntent
- /email/change-request
- /account/deletion-request

Per ADR-007 the envelope is declared explicitly on each endpoint, so the cached
body is a string and we return it verbatim with the original status code.
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger(__name__)

_IDEMPOTENT_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
_TTL_SECONDS = 24 * 60 * 60  # 24h
_MAX_BODY_BYTES = 256 * 1024  # 256 KB cap — bigger responses won't be cached


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

        cache_key = self._build_cache_key(request, key)

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
    def _build_cache_key(request: Request, idempotency_key: str) -> str:
        user = getattr(request.state, "user", None)
        user_id = str(getattr(user, "id", "anon")) if user else "anon"
        return f"idempotency:{user_id}:{request.method}:{request.url.path}:{idempotency_key}"
