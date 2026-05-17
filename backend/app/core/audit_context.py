"""
app/core/audit_context.py — request-scoped audit metadata bundle (hotfix H4).

Routers and services that need to record who-did-what-from-where (audit
log entries, user_login_history rows, pending contact change creation,
etc.) reach for three pieces of metadata: client IP, user-agent, and
request id. Today each call site reconstructs them by hand from
``request.client.host`` and ``request.headers.get("user-agent")``, which
is both repetitive and easy to get wrong (e.g. behind a proxy).

This module formalises the bundle into a single immutable dataclass that:

  - the ``RequestIDMiddleware`` populates once per request via
    ``AuditContext.from_request(request)`` (attached as
    ``request.state.audit_ctx``);
  - routers pull off ``request.state`` and pass explicitly to services;
  - services accept as a positional/keyword argument — never read
    ``request.state`` themselves (transport-layer leakage we want to
    avoid).

Existing call sites that take ``ip_address`` / ``user_agent`` as scalar
params keep working — ``AuditContext`` is purely additive. New code in
Phase 4+ should accept and forward the context directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request


@dataclass(frozen=True)
class AuditContext:
    """Forensic bundle for one HTTP request.

    Always safe to instantiate with all-None fields (e.g. for background
    workers writing audit entries with no associated request). The
    receiving service is responsible for treating missing fields as
    "unknown" rather than failing.
    """

    ip: str | None
    user_agent: str | None
    request_id: str | None

    @classmethod
    def from_request(cls, request: "Request") -> "AuditContext":
        return cls(
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=getattr(request.state, "request_id", None),
        )

    @classmethod
    def empty(cls) -> "AuditContext":
        """For non-HTTP code paths (workers, scripts). Treats as unknown
        rather than blowing up. Audit log will record NULL ip/UA."""
        return cls(ip=None, user_agent=None, request_id=None)
