"""
app/middleware/structured_logging.py — Emits one structured JSON line per request.

Fields: request_id, method, path, status, latency_ms, user_id (if authenticated),
client_ip, user_agent. Logged at INFO; errors are logged at WARNING/ERROR.

Skips noisy paths (/health, /metrics, /docs, /openapi.json) to keep aggregators clean.

Depends on `RequestIDMiddleware` being registered first.
"""
from __future__ import annotations

import logging
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("raycarwash.access")

_QUIET_PATHS = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path in _QUIET_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            logger.exception(
                "unhandled_exception",
                extra=_log_extra(request, status_code=500, latency_ms=_elapsed(start)),
            )
            raise
        finally:
            latency_ms = _elapsed(start)
            level = logging.INFO
            if 500 <= status_code < 600:
                level = logging.ERROR
            elif 400 <= status_code < 500:
                level = logging.WARNING
            logger.log(
                level,
                "http_request",
                extra=_log_extra(request, status_code=status_code, latency_ms=latency_ms),
            )


def _elapsed(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _log_extra(request: Request, *, status_code: int, latency_ms: float) -> dict:
    user = getattr(request.state, "user", None)
    user_id = str(getattr(user, "id", "")) if user else None
    client_ip = _client_ip(request)
    return {
        "method": request.method,
        "path": request.url.path,
        "query": request.url.query or None,
        "status": status_code,
        "latency_ms": latency_ms,
        "user_id": user_id,
        "client_ip": client_ip,
        "user_agent": request.headers.get("user-agent"),
    }


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
