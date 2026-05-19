"""
tests/test_idempotency_v2_user_scope.py — Plan 22 §6.1.3 (audit finding H1).

The legacy IdempotencyMiddleware path builds its cache key from
`request.state.user`, but FastAPI auth deps run AFTER middleware so
`state.user` is None at key-build time and the user_id falls back to
the literal "anon". Two different users sharing the same Idempotency-Key
on an empty-body mutation (PUT accept/decline) collide on the same
"anon:...:empty" cache slot — cross-user response replay.

The v2 fix moves the cache lookup into a post-auth dep
(`resolve_idempotency`). FastAPI evaluates auth deps before the dep
itself, so `current_user.id` is available when the v2 key is built:
    idemp:v2:{user_id}:{method}:{path}:{key}:{body_hash}

This file exercises the regression scenario from the audit:
- Two users, same Idempotency-Key, identical empty body, different
  expected responses → must NOT cross-contaminate.
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
    build_idempotency_v2_cache_key,
    resolve_idempotency,
)


class _FakeUser:
    """Minimal stand-in for User.id (a UUID)."""

    def __init__(self, user_id: UUID) -> None:
        self.id = user_id


class _FakeRedis:
    """Sufficient for the v2 dep + middleware write path."""

    def __init__(self) -> None:
        self.store: dict[str, dict[str, str]] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.store.get(key, {}))

    async def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.store.setdefault(key, {}).update(mapping)
        return len(mapping)

    async def expire(self, key: str, ttl: int) -> bool:
        return True


def _build_app(user: _FakeUser) -> tuple[FastAPI, _FakeRedis, list[dict[str, Any]]]:
    """Build a test app whose `get_current_user` always returns `user`.

    We override `Depends(get_current_user)` via FastAPI's dependency
    overrides so we don't have to thread a real JWT through the test.
    """
    from domains.auth.service import get_current_user

    app = FastAPI()
    redis = _FakeRedis()
    hits: list[dict[str, Any]] = []

    async def _fake_get_current_user() -> _FakeUser:
        return user

    app.dependency_overrides[get_current_user] = _fake_get_current_user

    # Replay exception → cached Response
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

    @app.put("/jobs/{job_id}/accept")
    async def accept(
        job_id: str,
        request: Request,
        _idem: None = Depends(resolve_idempotency),
    ):
        # Echo who accepted what so cross-user contamination is observable.
        hits.append({"user_id": str(user.id), "job_id": job_id})
        return {"accepted_by": str(user.id), "job_id": job_id}

    app.add_middleware(IdempotencyMiddleware)
    app.state.redis = redis
    return app, redis, hits


@pytest.mark.asyncio
async def test_v2_same_user_same_key_replays():
    """Single user retrying the same accept gets the cached response on retry."""
    user = _FakeUser(uuid4())
    app, redis, hits = _build_app(user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.put("/jobs/job-A/accept", headers={"Idempotency-Key": "k1"})
        r2 = await ac.put("/jobs/job-A/accept", headers={"Idempotency-Key": "k1"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Handler ran exactly once; second came from v2 cache.
    assert len(hits) == 1
    assert r2.headers.get("X-Idempotent-Replay") == "true"
    assert r1.json() == r2.json()


@pytest.mark.asyncio
async def test_v2_different_users_same_key_do_not_cross_contaminate():
    """The H1 regression case. Pre-fix: anon:k1:empty collides → user B
    receives user A's response. Post-fix: v2:UID_A:... ≠ v2:UID_B:..."""
    user_a = _FakeUser(uuid4())
    user_b = _FakeUser(uuid4())

    # Build separate apps because dependency_overrides is per-app and we
    # want each to authenticate as a different user.
    app_a, redis_a, hits_a = _build_app(user_a)
    app_b, redis_b, hits_b = _build_app(user_b)

    # Critically: both apps share the SAME redis backend so a v1-style bug
    # (anon collision) would be visible across both clients. We achieve
    # this by injecting the same _FakeRedis instance.
    shared = _FakeRedis()
    app_a.state.redis = shared
    app_b.state.redis = shared

    async with (
        AsyncClient(transport=ASGITransport(app=app_a), base_url="http://test") as ac_a,
        AsyncClient(transport=ASGITransport(app=app_b), base_url="http://test") as ac_b,
    ):
        r_a = await ac_a.put("/jobs/job-X/accept", headers={"Idempotency-Key": "shared"})
        r_b = await ac_b.put("/jobs/job-X/accept", headers={"Idempotency-Key": "shared"})

    assert r_a.status_code == 200
    assert r_b.status_code == 200
    # Both handlers ran — no cross-user replay.
    assert len(hits_a) == 1
    assert len(hits_b) == 1
    assert r_a.json()["accepted_by"] == str(user_a.id)
    assert r_b.json()["accepted_by"] == str(user_b.id)
    # Neither marked as replay.
    assert r_a.headers.get("X-Idempotent-Replay") is None
    assert r_b.headers.get("X-Idempotent-Replay") is None


@pytest.mark.asyncio
async def test_v2_cache_key_format():
    """Sanity check the key builder is producing the exact v2 format
    documented in the module docstring."""
    user_id = "11111111-2222-3333-4444-555555555555"
    key = build_idempotency_v2_cache_key(
        user_id=user_id,
        method="POST",
        path="/api/v1/detailers/me/earnings/cash-out",
        idempotency_key="abc123",
        body_hash="deadbeef00000000",
    )
    assert key == (
        f"idemp:v2:{user_id}:POST:/api/v1/detailers/me/earnings/cash-out:"
        "abc123:deadbeef00000000"
    )


@pytest.mark.asyncio
async def test_v2_no_idempotency_key_is_noop():
    """If the client doesn't send Idempotency-Key, the v2 dep must be a no-op
    (no Redis writes, no state mutations, no replay)."""
    user = _FakeUser(uuid4())
    app, redis, hits = _build_app(user)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r1 = await ac.put("/jobs/job-A/accept")
        r2 = await ac.put("/jobs/job-A/accept")

    # Both ran — no cache, no replay.
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(hits) == 2
    assert redis.store == {}
