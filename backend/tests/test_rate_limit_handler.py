"""
tests/test_rate_limit_handler.py — Plan 19/20/21 §"Operational Requirements"
mandate that 429 responses use the `ErrorEnvelope` shape and include a
`Retry-After` header. The default slowapi handler returns its own
`{"error": "Rate limit exceeded: ..."}` payload without `Retry-After`,
so we override.

These tests build a minimal FastAPI app with a 1-request-per-minute
endpoint and verify:
- First request gets a normal 200.
- Second request inside the window gets 429.
- 429 response has `Retry-After` header.
- 429 body shape depends on path prefix:
    * `/api/v1/*` → ErrorEnvelope (code `rate_limit_exceeded`)
    * other prefixes → legacy `{"error": "Rate limit exceeded: ..."}`
      shape preserved so un-migrated callers don't break.

Each test instantiates a fresh `Limiter` so the in-memory storage never
bleeds across tests (slowapi keys storage by view-func name, and we
reuse `ping` across the test app builds).
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.exception_handlers import register_exception_handlers


def _build_app(path: str = "/api/v1/ping") -> FastAPI:
    """Mount a single rate-limited GET on a fresh Limiter. Path prefix
    decides whether the handler returns ErrorEnvelope or the legacy shape.
    """
    app = FastAPI()
    fresh_limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = fresh_limiter
    register_exception_handlers(app)

    @app.get(path)
    @fresh_limiter.limit("1/minute")
    async def ping(request: Request):
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_first_request_succeeds_second_returns_429_envelope():
    app = _build_app("/api/v1/ping")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.get("/api/v1/ping")
        r2 = await ac.get("/api/v1/ping")

    assert r1.status_code == 200
    assert r2.status_code == 429

    # Retry-After header present and a positive integer
    retry_after = r2.headers.get("Retry-After")
    assert retry_after is not None
    assert int(retry_after) > 0

    # ErrorEnvelope shape (envelope path)
    body = r2.json()
    assert "error" in body
    assert body["error"]["code"] == "rate_limit_exceeded"
    # Message references the limit and retry time
    assert "Retry" in body["error"]["message"] or "1 per 1 minute" in body["error"]["message"]


@pytest.mark.asyncio
async def test_429_on_legacy_path_keeps_simple_shape():
    """Routes outside /api/v1/* (legacy) should preserve the existing
    `{"error": "Rate limit exceeded: ..."}` shape so older clients
    don't break."""
    app = _build_app("/legacy/ping")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.get("/legacy/ping")
        r2 = await ac.get("/legacy/ping")

    assert r1.status_code == 200
    assert r2.status_code == 429
    assert r2.headers.get("Retry-After") is not None

    body = r2.json()
    # Legacy shape: top-level "error" string, NOT the envelope shape
    assert "error" in body
    assert isinstance(body["error"], str)
    assert "Rate limit exceeded" in body["error"]


@pytest.mark.asyncio
async def test_429_retry_after_matches_window():
    """`Retry-After` should reflect the rate-limit window (in seconds).
    For `1/minute` this must be 60."""
    app = _build_app("/api/v1/ping")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.get("/api/v1/ping")
        r2 = await ac.get("/api/v1/ping")

    assert r2.status_code == 429
    assert int(r2.headers["Retry-After"]) == 60
