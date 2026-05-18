"""
tests/test_audit_context.py — Hotfix H4.

Verifies the AuditContext dataclass and its automatic population by the
RequestIDMiddleware. Phase 4 routers will pull
``request.state.audit_ctx`` and pass it to services explicitly; this
test pins the contract so the wiring can't silently regress.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.audit_context import AuditContext
from app.middleware.request_id import RequestIDMiddleware


def test_audit_context_empty_factory_returns_all_none():
    ctx = AuditContext.empty()
    assert ctx.ip is None
    assert ctx.user_agent is None
    assert ctx.request_id is None


def test_audit_context_is_frozen():
    """Immutability matters — once the request enters a service we don't
    want some inner layer mutating the forensics."""
    ctx = AuditContext(ip="1.2.3.4", user_agent="curl/8", request_id="req_abc")
    with pytest.raises(Exception):  # FrozenInstanceError subclass of AttributeError
        ctx.ip = "9.9.9.9"  # type: ignore[misc]


@pytest.mark.asyncio
async def test_middleware_populates_audit_ctx_on_request_state():
    app = FastAPI()
    captured: dict = {}

    @app.get("/probe")
    async def probe(request: Request):
        ctx = getattr(request.state, "audit_ctx", None)
        captured["ctx"] = ctx
        return {"ok": True}

    app.add_middleware(RequestIDMiddleware)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/probe", headers={"User-Agent": "RegressionBot/1.0"})

    assert resp.status_code == 200
    ctx = captured["ctx"]
    assert ctx is not None
    assert isinstance(ctx, AuditContext)
    # ASGITransport doesn't simulate a real client tuple, so ip may be None
    # — that's fine; the contract is that the dataclass is constructed
    # and request_id + user_agent are populated.
    assert ctx.user_agent == "RegressionBot/1.0"
    assert ctx.request_id is not None
    assert ctx.request_id.startswith("req_")


@pytest.mark.asyncio
async def test_middleware_honors_incoming_request_id_in_audit_ctx():
    """If the client sends a permissible X-Request-ID, AuditContext.request_id
    reflects it — useful for tracing across services."""
    app = FastAPI()
    captured: dict = {}

    @app.get("/probe")
    async def probe(request: Request):
        captured["ctx"] = request.state.audit_ctx
        return {"ok": True}

    app.add_middleware(RequestIDMiddleware)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        resp = await ac.get("/probe", headers={"X-Request-ID": "trace_abc12345"})

    assert resp.status_code == 200
    assert captured["ctx"].request_id == "trace_abc12345"
