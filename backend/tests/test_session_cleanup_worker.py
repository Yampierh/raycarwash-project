"""
tests/test_session_cleanup_worker.py — Plan 23 Fase 8.

Covers the daily session GC worker:

  - Auto-revoke: sessions whose refresh-token family has expired beyond
    the grace period are flipped to revoked=True with revoked_at=now.
  - Active sessions whose family is still valid are NOT touched.
  - Hard-delete: sessions revoked > 90 days ago are physically deleted.
  - Cache eviction: every touched session id gets its Redis entries
    deleted (best-effort, non-fatal when redis is down).
  - Idempotent: running twice in a row produces zero work the second time.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import RefreshToken, Session
from domains.auth.refresh_token_repository import RefreshTokenRepository
from domains.auth.session_repository import SessionRepository
from tests.conftest import _create_user_with_role


def _make_app_state(redis=None):
    return SimpleNamespace(redis=redis)


async def _make_session_with_family(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    family_expires_at: datetime,
    revoked: bool = False,
    revoked_at: datetime | None = None,
) -> uuid.UUID:
    """Create a Session row + a backing RefreshToken row in the same
    family. The worker walks the family's expires_at to decide whether
    the session is dead."""
    family_id = uuid.uuid4()

    # Refresh token row — use the repo so the hash + expiry shape match.
    raw = uuid.uuid4().hex  # any random string; we don't redeem it
    await RefreshTokenRepository(db).create(
        user_id=user_id,
        raw_token=raw,
        family_id=family_id,
        expires_at=family_expires_at,
    )

    sess = Session(
        user_id=user_id,
        family_id=family_id,
        device_name="UA",
        device_type="api",
        ip_address="127.0.0.1",
        user_agent="UA",
        revoked=revoked,
        revoked_at=revoked_at,
    )
    db.add(sess)
    await db.flush()
    await db.commit()
    return sess.id


# ── Auto-revoke ────────────────────────────────────────────────────── #


class TestAutoRevoke:
    @pytest.mark.asyncio
    async def test_expired_family_session_revoked(
        self, db_session: AsyncSession, monkeypatch,
    ):
        """Family expired > grace days ago → session must be revoked."""
        from workers import session_cleanup_worker as worker
        # Patch AsyncSessionLocal so the worker sees the test fixture DB.
        monkeypatch.setattr(
            worker,
            "AsyncSessionLocal",
            lambda: _SessionFromFixture(db_session),
        )

        user = await _create_user_with_role(db_session, "exp@test.com", "E", "client")
        now = datetime.now(timezone.utc)
        sid = await _make_session_with_family(
            db_session, user.id,
            family_expires_at=now - timedelta(days=5),  # 5d past expiry
        )

        stats = await worker._run_once(_make_app_state(None))
        assert stats["sessions_revoked"] == 1

        row = (await db_session.execute(
            select(Session).where(Session.id == sid)
        )).scalar_one()
        await db_session.refresh(row)
        assert row.revoked is True
        assert row.revoked_at is not None

    @pytest.mark.asyncio
    async def test_active_session_not_touched(
        self, db_session: AsyncSession, monkeypatch,
    ):
        from workers import session_cleanup_worker as worker
        monkeypatch.setattr(
            worker,
            "AsyncSessionLocal",
            lambda: _SessionFromFixture(db_session),
        )

        user = await _create_user_with_role(db_session, "active@test.com", "A", "client")
        now = datetime.now(timezone.utc)
        sid = await _make_session_with_family(
            db_session, user.id,
            family_expires_at=now + timedelta(days=3),
        )

        stats = await worker._run_once(_make_app_state(None))
        assert stats["sessions_revoked"] == 0

        row = (await db_session.execute(
            select(Session).where(Session.id == sid)
        )).scalar_one()
        await db_session.refresh(row)
        assert row.revoked is False


# ── Hard delete ────────────────────────────────────────────────────── #


class TestHardDelete:
    @pytest.mark.asyncio
    async def test_old_revoked_session_deleted(
        self, db_session: AsyncSession, monkeypatch,
    ):
        from workers import session_cleanup_worker as worker
        monkeypatch.setattr(
            worker,
            "AsyncSessionLocal",
            lambda: _SessionFromFixture(db_session),
        )

        user = await _create_user_with_role(db_session, "old@test.com", "O", "client")
        now = datetime.now(timezone.utc)
        old_revoked_at = now - timedelta(days=120)
        sid = await _make_session_with_family(
            db_session, user.id,
            family_expires_at=now + timedelta(days=1),  # still valid
            revoked=True,
            revoked_at=old_revoked_at,
        )

        stats = await worker._run_once(_make_app_state(None))
        assert stats["sessions_deleted"] == 1

        gone = (await db_session.execute(
            select(Session).where(Session.id == sid)
        )).scalar_one_or_none()
        assert gone is None

    @pytest.mark.asyncio
    async def test_recently_revoked_session_kept(
        self, db_session: AsyncSession, monkeypatch,
    ):
        """30 days < 90 day cutoff → keep."""
        from workers import session_cleanup_worker as worker
        monkeypatch.setattr(
            worker,
            "AsyncSessionLocal",
            lambda: _SessionFromFixture(db_session),
        )

        user = await _create_user_with_role(db_session, "recent@test.com", "R", "client")
        now = datetime.now(timezone.utc)
        sid = await _make_session_with_family(
            db_session, user.id,
            family_expires_at=now + timedelta(days=1),
            revoked=True,
            revoked_at=now - timedelta(days=30),
        )

        stats = await worker._run_once(_make_app_state(None))
        assert stats["sessions_deleted"] == 0

        still_there = (await db_session.execute(
            select(Session).where(Session.id == sid)
        )).scalar_one_or_none()
        assert still_there is not None


# ── Cache eviction ─────────────────────────────────────────────────── #


class TestCacheEviction:
    @pytest.mark.asyncio
    async def test_revoked_session_evicts_cache(
        self, db_session: AsyncSession, monkeypatch,
    ):
        from workers import session_cleanup_worker as worker
        monkeypatch.setattr(
            worker,
            "AsyncSessionLocal",
            lambda: _SessionFromFixture(db_session),
        )

        user = await _create_user_with_role(db_session, "evict@test.com", "E", "client")
        now = datetime.now(timezone.utc)
        sid = await _make_session_with_family(
            db_session, user.id,
            family_expires_at=now - timedelta(days=5),
        )

        redis = AsyncMock()
        redis.delete = AsyncMock()
        stats = await worker._run_once(_make_app_state(redis))
        assert stats["sessions_revoked"] == 1
        # 2 delete calls per session (session:<sid> + session:last_seen:<sid>)
        assert redis.delete.await_count >= 2
        # The session id appears in one of the keys
        called_keys = [c.args[0] for c in redis.delete.await_args_list]
        assert any(str(sid) in key for key in called_keys)

    @pytest.mark.asyncio
    async def test_no_redis_is_noop(
        self, db_session: AsyncSession, monkeypatch,
    ):
        """app_state without redis → cache eviction returns 0, no crash."""
        from workers import session_cleanup_worker as worker
        monkeypatch.setattr(
            worker,
            "AsyncSessionLocal",
            lambda: _SessionFromFixture(db_session),
        )

        user = await _create_user_with_role(db_session, "norr@test.com", "N", "client")
        now = datetime.now(timezone.utc)
        await _make_session_with_family(
            db_session, user.id,
            family_expires_at=now - timedelta(days=5),
        )

        stats = await worker._run_once(_make_app_state(None))
        assert stats["cache_evicted"] == 0


# ── Idempotency ────────────────────────────────────────────────────── #


class TestIdempotency:
    @pytest.mark.asyncio
    async def test_second_run_is_zero_work(
        self, db_session: AsyncSession, monkeypatch,
    ):
        from workers import session_cleanup_worker as worker
        monkeypatch.setattr(
            worker,
            "AsyncSessionLocal",
            lambda: _SessionFromFixture(db_session),
        )

        user = await _create_user_with_role(db_session, "idem@test.com", "I", "client")
        now = datetime.now(timezone.utc)
        await _make_session_with_family(
            db_session, user.id,
            family_expires_at=now - timedelta(days=5),
        )

        first = await worker._run_once(_make_app_state(None))
        second = await worker._run_once(_make_app_state(None))
        assert first["sessions_revoked"] == 1
        assert second["sessions_revoked"] == 0
        assert second["sessions_deleted"] == 0


# ── Test util — AsyncSessionLocal stand-in for the worker ──────────── #


class _SessionFromFixture:
    """Async context manager that yields the test's db_session AsyncSession
    instead of opening a new one. The worker normally does
    `async with AsyncSessionLocal() as db: ...`; we patch
    `AsyncSessionLocal` to return an instance of this class so the same
    session (already committed by setup helpers) is reused.

    Crucially, `commit()` on the test session is intercepted — the
    fixture owns lifecycle, so we just `flush()` here. Otherwise the
    second `commit()` would close the transaction and break later
    queries in the same test."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def __aenter__(self):
        # Wrap commit so it doesn't break the outer fixture's transaction.
        self._orig_commit = self._session.commit
        async def _flush_only():
            await self._session.flush()
        self._session.commit = _flush_only  # type: ignore[assignment]
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        self._session.commit = self._orig_commit  # type: ignore[assignment]
        # Caller (fixture) handles final close.
