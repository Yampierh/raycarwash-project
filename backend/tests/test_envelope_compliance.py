"""
tests/test_envelope_compliance.py — Phase 0 compliance test.

Asserts that every NEW route registered under /api/v1/users/me/* (and other
Phase 0+ paths) declares a response_model that derives from Envelope.

Strategy: walk app.router.routes after app construction and check each one.
This is the CI safety net for ADR-007. Legacy paths are skipped via the
allow-list below — they'll be migrated to envelope as part of their phase.

When this test fails, a misconfigured route is registered. Fix it by:
  1. Adding `response_model=Envelope[YourSchema]` to the endpoint
  2. OR marking it with `@envelope_exempt` if it serves a non-JSON body
  3. OR moving it onto an `EnvelopeRouter` instead of bare `APIRouter`
     (EnvelopeRouter fails at startup, not at test time — preferred)
"""
from __future__ import annotations

import pytest
from fastapi.datastructures import DefaultPlaceholder
from fastapi.routing import APIRoute

from main import app
from shared.schemas import Envelope, ErrorEnvelope, PaginatedEnvelope


# Paths that pre-date Phase 0 and have not been migrated yet. As phases land,
# these prefixes are removed and the routes must be on EnvelopeRouter.
LEGACY_PATH_PREFIXES: tuple[str, ...] = (
    "/auth/",
    "/api/v1/admin/",
    "/api/v1/addons",
    "/api/v1/appointments",
    "/api/v1/detailers",
    "/api/v1/fares",
    "/api/v1/matching",
    "/api/v1/notifications",
    "/api/v1/payments",
    "/api/v1/reviews",
    "/api/v1/rides",
    "/api/v1/services",
    "/api/v1/vehicles",
    "/webhooks/",
    "/.well-known/",
    "/dev/",          # development-only utilities (LocalStorageAdapter upload sink)
    "/storage/",      # local static mount for LocalStorageAdapter downloads
)

# Routes that legitimately return non-JSON (file streams, redirects, etc.)
EXPLICIT_EXEMPT_PATHS: tuple[str, ...] = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
)


def _is_envelope_model(model) -> bool:
    if model is None or isinstance(model, DefaultPlaceholder):
        return False
    origin = getattr(model, "__pydantic_generic_metadata__", {}).get("origin")
    candidates = (Envelope, PaginatedEnvelope, ErrorEnvelope)
    if origin in candidates:
        return True
    try:
        if isinstance(model, type) and issubclass(model, candidates):
            return True
    except TypeError:
        pass
    return False


def _should_check(route: APIRoute) -> bool:
    if route.path in EXPLICIT_EXEMPT_PATHS:
        return False
    if any(route.path.startswith(p) for p in LEGACY_PATH_PREFIXES):
        return False
    # 204 No Content is allowed to have no body
    if route.status_code == 204:
        return False
    # Endpoints decorated with @envelope_exempt opt out explicitly
    if getattr(route.endpoint, "_envelope_exempt", False):
        return False
    return True


def test_all_new_routes_use_envelope():
    """Every /api/v1/users/me/* route (and equivalents added after Phase 0)
    must declare response_model derived from Envelope/PaginatedEnvelope/ErrorEnvelope."""
    offenders: list[str] = []

    for route in app.router.routes:
        if not isinstance(route, APIRoute):
            continue
        if not _should_check(route):
            continue
        if not _is_envelope_model(route.response_model):
            offenders.append(f"{','.join(sorted(route.methods))} {route.path}")

    assert not offenders, (
        "The following routes are missing an Envelope response_model. "
        "Either declare `response_model=Envelope[T]` on the route, register it on "
        "`EnvelopeRouter` (preferred — fails fast at startup), or apply `@envelope_exempt` "
        "if it serves non-JSON content:\n  - " + "\n  - ".join(offenders)
    )


def test_envelope_router_rejects_bare_models():
    """EnvelopeRouter must raise EnvelopeContractError when a route is registered
    without a compliant response_model."""
    from app.core.envelope_router import EnvelopeRouter, EnvelopeContractError
    from pydantic import BaseModel

    class _Foo(BaseModel):
        x: int

    router = EnvelopeRouter()

    with pytest.raises(EnvelopeContractError):

        @router.get("/bad", response_model=_Foo)
        async def _bad():
            return {"x": 1}


def test_envelope_router_accepts_envelope_t():
    """EnvelopeRouter must accept Envelope[T], PaginatedEnvelope[T], 204, and exempt."""
    from app.core.envelope_router import EnvelopeRouter, envelope_exempt
    from pydantic import BaseModel

    class _Foo(BaseModel):
        x: int

    router = EnvelopeRouter()

    @router.get("/ok-envelope", response_model=Envelope[_Foo])
    async def _ok():
        return Envelope(data=_Foo(x=1))

    @router.get("/ok-paginated", response_model=PaginatedEnvelope[_Foo])
    async def _ok_pag():
        return PaginatedEnvelope(data=[_Foo(x=1)], meta={"limit": 20, "has_more": False})

    @router.delete("/ok-204", status_code=204)
    async def _ok_204():
        return None

    @router.get("/ok-exempt")
    @envelope_exempt
    async def _ok_exempt():
        return b"stream"

    # If we got here without raising, all four shapes are accepted.
