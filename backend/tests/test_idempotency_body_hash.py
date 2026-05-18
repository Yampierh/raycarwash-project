"""
tests/test_idempotency_body_hash.py — Hotfix H2.

Regression guard for the idempotency cache-key collision fixed in
IdempotencyMiddleware. Before the fix, the cache key was
    `idempotency:{user}:{method}:{path}:{key}`
so two requests sharing an Idempotency-Key but carrying different bodies
would hit the same slot — the second caller received the first caller's
response. On payments, that meant a user retrying a setup-intent with a
corrected amount could end up charged against the original amount/card.

The fix binds a SHA-256 prefix of the request body to the cache key:
    `idempotency:{user}:{method}:{path}:{key}:{body_hash}`
Different bodies = different cache slots = both executed and cached
independently. Identical replays still hit the cache.

Crucially, the middleware must re-attach the consumed body to
`request._receive` so downstream handlers can still parse it — verified
by the "body reaches handler" tests below.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.idempotency import IdempotencyMiddleware


class _FakeRedis:
    """In-memory stand-in for redis.asyncio.Redis. Stores hashes keyed by
    string, ignores TTLs. Sufficient to exercise the middleware's
    serve-cached vs cache-miss branches."""

    def __init__(self) -> None:
        self.store: dict[str, dict[str, str]] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.store.get(key, {}))

    async def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.store.setdefault(key, {}).update(mapping)
        return len(mapping)

    async def expire(self, key: str, ttl: int) -> bool:
        return True


def _build_app() -> tuple[FastAPI, _FakeRedis, list[dict[str, Any]]]:
    """Tiny FastAPI app with one POST that echoes its body and counts hits.

    Note: httpx.ASGITransport does NOT fire lifespan events by default, so
    we bind app.state.redis directly rather than via @app.on_event.
    """
    app = FastAPI()
    redis = _FakeRedis()
    hits: list[dict[str, Any]] = []

    @app.post("/echo")
    async def echo(payload: dict, request: Request):
        hits.append(payload)
        return {"received": payload, "hit_count": len(hits)}

    app.add_middleware(IdempotencyMiddleware)
    app.state.redis = redis
    return app, redis, hits


@pytest.mark.asyncio
async def test_same_key_same_body_replays_cache():
    app, redis, hits = _build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        body = {"amount_cents": 1500}
        r1 = await ac.post("/echo", json=body, headers={"Idempotency-Key": "abc"})
        r2 = await ac.post("/echo", json=body, headers={"Idempotency-Key": "abc"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Handler ran exactly once — second response came from cache.
    assert len(hits) == 1
    # Cache replay carries the marker header.
    assert r2.headers.get("X-Idempotent-Replay") == "true"
    assert r1.json() == r2.json()


@pytest.mark.asyncio
async def test_same_key_different_body_executes_separately():
    """The critical regression case. Pre-fix, the second call would have
    returned r1's body (wrong); post-fix the body hash makes them distinct
    cache slots and the handler runs twice."""
    app, redis, hits = _build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post(
            "/echo", json={"amount_cents": 1500}, headers={"Idempotency-Key": "k1"}
        )
        r2 = await ac.post(
            "/echo", json={"amount_cents": 9999}, headers={"Idempotency-Key": "k1"}
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both bodies were processed — no cross-contamination.
    assert len(hits) == 2
    assert hits[0] == {"amount_cents": 1500}
    assert hits[1] == {"amount_cents": 9999}
    assert r1.json()["received"] == {"amount_cents": 1500}
    assert r2.json()["received"] == {"amount_cents": 9999}
    # Neither response is a replay.
    assert r1.headers.get("X-Idempotent-Replay") is None
    assert r2.headers.get("X-Idempotent-Replay") is None


@pytest.mark.asyncio
async def test_body_is_reattached_for_downstream_handler():
    """Direct evidence that the middleware's body consumption doesn't
    starve the handler. Without the request._receive re-attachment, this
    test would 422 (FastAPI would see an empty JSON body)."""
    app, redis, hits = _build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/echo",
            json={"vehicle": "Camry", "year": 2020},
            headers={"Idempotency-Key": "reattach-check"},
        )
    assert resp.status_code == 200
    assert resp.json()["received"] == {"vehicle": "Camry", "year": 2020}


@pytest.mark.asyncio
async def test_no_idempotency_key_bypasses_middleware():
    """Requests without the header must pass through untouched."""
    app, redis, hits = _build_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/echo", json={"x": 1})
        r2 = await ac.post("/echo", json={"x": 1})
    # No cache, no header — both execute and increment hit count.
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(hits) == 2
    assert r1.headers.get("X-Idempotent-Replay") is None
    assert r2.headers.get("X-Idempotent-Replay") is None


@pytest.mark.asyncio
async def test_get_method_bypasses_middleware():
    app = FastAPI()
    redis = _FakeRedis()
    hits: list[int] = []

    @app.get("/ping")
    async def ping():
        hits.append(1)
        return {"ok": True}

    app.add_middleware(IdempotencyMiddleware)
    app.state.redis = redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.get("/ping", headers={"Idempotency-Key": "ignored-on-get"})
        await ac.get("/ping", headers={"Idempotency-Key": "ignored-on-get"})

    # GET is not in _IDEMPOTENT_METHODS — handler runs both times.
    assert len(hits) == 2


@pytest.mark.asyncio
async def test_redis_outage_falls_open():
    """If Redis can't be read, the request still executes (fail-open).
    Better to lose idempotency convenience than to 500 the user."""
    app = FastAPI()
    hits: list[int] = []

    class BrokenRedis:
        async def hgetall(self, key):
            raise RuntimeError("redis is unreachable")

        async def hset(self, key, mapping):
            raise RuntimeError("redis is unreachable")

        async def expire(self, key, ttl):
            raise RuntimeError("redis is unreachable")

    @app.post("/ping")
    async def ping(payload: dict):
        hits.append(1)
        return {"ok": True}

    app.add_middleware(IdempotencyMiddleware)
    app.state.redis = BrokenRedis()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/ping", json={"k": "v"}, headers={"Idempotency-Key": "abc"})

    assert resp.status_code == 200
    assert len(hits) == 1
