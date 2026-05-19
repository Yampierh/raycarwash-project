"""
tests/test_idempotency_body_hash.py — body-hash isolation regression guard.

Originally Hotfix H2. After the H1 refactor (Plan 22 §6.1.3) the cache
lookup moved out of the middleware into a post-auth dep
(`resolve_idempotency`), so these tests now wire a fake `get_current_user`
override and declare `Depends(resolve_idempotency)` on the test route.
The body-hash binding behaviour they verify is unchanged:

  Cache key (v2):
      idemp:v2:{user_id}:{method}:{path}:{key}:{body_hash}

  Different body bytes = different body_hash = different cache slot.
  Identical body bytes = identical hash = replay.

Crucially, the middleware must re-attach the consumed body to
`request._receive` so downstream handlers can still parse it — verified
by the "body reaches handler" test below.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.core.idempotency import (
    IdempotencyMiddleware,
    _IdempotentReplay,
    resolve_idempotency,
)


class _FakeUser:
    def __init__(self, user_id: UUID) -> None:
        self.id = user_id


class _FakeRedis:
    """In-memory stand-in for redis.asyncio.Redis. Stores hashes keyed by
    string, ignores TTLs. Sufficient to exercise the dep's cache slots
    plus the middleware's response-write path."""

    def __init__(self) -> None:
        self.store: dict[str, dict[str, str]] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.store.get(key, {}))

    async def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.store.setdefault(key, {}).update(mapping)
        return len(mapping)

    async def expire(self, key: str, ttl: int) -> bool:
        return True


def _build_app(
    user: _FakeUser | None = None,
    *,
    declare_dep: bool = True,
) -> tuple[FastAPI, _FakeRedis, list[dict[str, Any]]]:
    """Tiny FastAPI app with one POST that echoes its body and counts hits.

    `user=None` builds an app whose route does NOT declare `Depends(resolve_idempotency)`
    — used to verify that routes which haven't opted in get zero caching
    behaviour (only body capture / receive replay).

    Note: httpx.ASGITransport does NOT fire lifespan events by default, so
    we bind app.state.redis directly rather than via @app.on_event.
    """
    from domains.auth.service import get_current_user

    app = FastAPI()
    redis = _FakeRedis()
    hits: list[dict[str, Any]] = []

    if user is not None:
        async def _fake_get_current_user() -> _FakeUser:
            return user

        app.dependency_overrides[get_current_user] = _fake_get_current_user

    @app.exception_handler(_IdempotentReplay)
    async def _replay(_request: Request, exc: _IdempotentReplay):
        from fastapi.responses import Response as FastAPIResponse

        return FastAPIResponse(
            content=exc.body,
            status_code=exc.status_code,
            headers={
                "content-type": exc.content_type,
                "X-Idempotent-Replay": "true",
            },
        )

    if declare_dep:
        @app.post("/echo")
        async def echo(
            payload: dict,
            request: Request,
            _idem: None = Depends(resolve_idempotency),
        ):
            hits.append(payload)
            return {"received": payload, "hit_count": len(hits)}
    else:
        @app.post("/echo")
        async def echo(payload: dict, request: Request):
            hits.append(payload)
            return {"received": payload, "hit_count": len(hits)}

    app.add_middleware(IdempotencyMiddleware)
    app.state.redis = redis
    return app, redis, hits


@pytest.mark.asyncio
async def test_same_key_same_body_replays_cache():
    user = _FakeUser(uuid4())
    app, redis, hits = _build_app(user)
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
    """The critical body-hash regression case. Different body bytes →
    different cache slots → handler runs twice. Identical responses are
    NOT cross-served."""
    user = _FakeUser(uuid4())
    app, redis, hits = _build_app(user)
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
    user = _FakeUser(uuid4())
    app, redis, hits = _build_app(user)
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
    user = _FakeUser(uuid4())
    app, redis, hits = _build_app(user)
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
    user = _FakeUser(uuid4())

    class BrokenRedis:
        async def hgetall(self, key):
            raise RuntimeError("redis is unreachable")

        async def hset(self, key, mapping):
            raise RuntimeError("redis is unreachable")

        async def expire(self, key, ttl):
            raise RuntimeError("redis is unreachable")

    app, _redis, hits = _build_app(user)
    app.state.redis = BrokenRedis()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/echo", json={"k": "v"}, headers={"Idempotency-Key": "abc"}
        )

    assert resp.status_code == 200
    assert len(hits) == 1


@pytest.mark.asyncio
async def test_route_without_dep_gets_no_cache_replay():
    """H1 fix consequence: routes that don't declare `Depends(resolve_idempotency)`
    do NOT get cross-request replay. They only get body capture + receive
    replay (so handlers still parse the body correctly). This is the
    documented behaviour for un-migrated legacy routes."""
    app, redis, hits = _build_app(user=None, declare_dep=False)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.post("/echo", json={"x": 1}, headers={"Idempotency-Key": "abc"})
        r2 = await ac.post("/echo", json={"x": 1}, headers={"Idempotency-Key": "abc"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both ran — no v2 dep was declared, so no caching happened.
    assert len(hits) == 2
    assert redis.store == {}
