"""
app/middleware/audit_context.py — Captures `ip`, `user_agent`, `request_id`
into `request.state.audit_ctx` so the AuditLogger can record them on every
mutation without routers having to pass them manually.

Order in main.py: RequestIDMiddleware → StructuredLoggingMiddleware → AuditContextMiddleware.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass(frozen=True)
class AuditContext:
    request_id: str | None
    ip_address: str | None
    user_agent: str | None


class AuditContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request.state.audit_ctx = AuditContext(
            request_id=getattr(request.state, "request_id", None),
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        return await call_next(request)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def get_audit_context(request: Request) -> AuditContext:
    """Convenience helper for services/repositories to read the audit context."""
    ctx = getattr(request.state, "audit_ctx", None)
    if ctx is None:
        return AuditContext(request_id=None, ip_address=None, user_agent=None)
    return ctx
