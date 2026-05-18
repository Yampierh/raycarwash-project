"""
app/middleware/request_id.py — Generates a per-request ULID and attaches it
to:

  - `request.state.request_id`     (read by handlers and auth)
  - `request_id_var` ContextVar    (read by structured logging)
  - response header `X-Request-ID` (read by clients for support tickets)

ULID is used instead of UUIDv4 because it sorts lexicographically by time —
useful when grepping logs. If the client sends `X-Request-ID` we honor it
(allows tracing across services) provided it matches a permissive shape.
"""
from __future__ import annotations

import re
import secrets
import string
import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging_context import request_id_var

# Lightweight ULID-like ID: 26 chars, base32 (Crockford). Sort-friendly.
_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_INCOMING_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def _generate_request_id() -> str:
    # 48-bit timestamp + 80-bit randomness = 26 base32 chars
    ts_ms = int(time.time() * 1000)
    ts_part = "".join(
        _BASE32[(ts_ms >> shift) & 0x1F] for shift in range(45, -5, -5)
    )  # 10 chars
    rand_part = "".join(_BASE32[secrets.randbelow(32)] for _ in range(16))
    return f"req_{ts_part}{rand_part}"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Must be registered FIRST so all downstream middleware/handlers see request_id."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        if incoming and _INCOMING_RE.match(incoming):
            request_id = incoming
        else:
            request_id = _generate_request_id()

        request.state.request_id = request_id
        # request.state.audit_ctx is populated downstream by
        # AuditContextMiddleware (see app/middleware/audit_context.py), which
        # also handles X-Forwarded-For. RequestID just runs first so the
        # downstream middleware can read request.state.request_id.
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
