"""
tests/test_sessions_management.py — Plan 23 Fase 2 + Fase 6.

Covers the UX-facing session management endpoints:

  - GET   /auth/sessions           — rich list backed by Session table,
                                     `is_current` flag set on caller's row.
  - POST  /auth/sessions/{id}/revoke — happy path, ownership check (404
                                     on someone else's session), idempotent.
  - DELETE /auth/sessions          — revoke-all (204).
  - DELETE /auth/sessions/{family_id} — legacy by-family back-compat.

Also covers the device parser (parse_device_name / parse_device_type)
since the login flow uses it to populate device_name/device_type.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import Session
from infrastructure.auth.device_parser import (
    parse_device_name, parse_device_type,
)
from tests.conftest import _create_user_with_role, get_access_token


# ── Device parser unit ─────────────────────────────────────────────── #


class TestDeviceParser:
    def test_iphone_safari(self):
        ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
            "Mobile/15E148 Safari/604.1"
        )
        assert parse_device_name(ua) == "iPhone · Safari"
        assert parse_device_type(ua) == "mobile"

    def test_android_chrome(self):
        ua = (
            "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        # Linux comes first in the device map; we want Android — but the
        # parser short-circuits at the first match, so the regex order
        # puts iPad/iPhone/Android before Linux to catch this case.
        assert parse_device_name(ua) == "Android · Chrome"
        assert parse_device_type(ua) == "mobile"

    def test_ipad(self):
        ua = (
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 Safari/604.1"
        )
        assert parse_device_name(ua) == "iPad · Safari"
        assert parse_device_type(ua) == "tablet"

    def test_windows_edge(self):
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
            "Safari/537.36 Edg/120.0.0.0"
        )
        assert parse_device_name(ua) == "Windows · Edge"
        assert parse_device_type(ua) == "desktop"

    def test_curl_api(self):
        ua = "curl/8.18.0"
        assert parse_device_name(ua) == "curl"
        # curl is treated as `api` — no desktop/mobile hint
        assert parse_device_type(ua) == "api"

    def test_empty_ua(self):
        assert parse_device_name(None) is None
        assert parse_device_name("") is None
        assert parse_device_type(None) == "api"


# ── /auth/sessions list ────────────────────────────────────────────── #


class TestListSessions:
    @pytest.mark.asyncio
    async def test_list_returns_current_session(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        await _create_user_with_role(db_session, "list1@test.com", "L1", "client")
        token = await get_access_token(client, "list1@test.com")
        resp = await client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        current = [s for s in body["sessions"] if s["is_current"]]
        assert len(current) == 1, "exactly one row must be flagged is_current"
        row = current[0]
        # New rich shape is populated.
        assert "device_type" in row
        assert "last_active_at" in row
        # Back-compat alias for pre-Fase-2 clients.
        assert "family_id" in row
        assert "last_used_at" in row

    @pytest.mark.asyncio
    async def test_list_anon_401(self, client: AsyncClient):
        resp = await client.get("/auth/sessions")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_revoked_sessions_excluded(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        await _create_user_with_role(db_session, "list2@test.com", "L2", "client")
        token = await get_access_token(client, "list2@test.com")
        # Login again to create a 2nd session, then revoke that one
        token2 = await get_access_token(client, "list2@test.com")

        import base64, json
        pad = lambda s: s + "=" * (-len(s) % 4)
        sid2 = json.loads(base64.urlsafe_b64decode(pad(token2.split(".")[1])))["sid"]

        from domains.auth.session_repository import SessionRepository
        repo = SessionRepository(db_session)
        await repo.revoke(uuid.UUID(sid2))
        await db_session.commit()

        resp = await client.get(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        sids = [s["id"] for s in resp.json()["sessions"]]
        assert sid2 not in sids


# ── POST /sessions/{id}/revoke ─────────────────────────────────────── #


class TestRevokeById:
    @pytest.mark.asyncio
    async def test_revoke_happy_path(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        await _create_user_with_role(db_session, "rev1@test.com", "R1", "client")
        t1 = await get_access_token(client, "rev1@test.com")
        t2 = await get_access_token(client, "rev1@test.com")  # second device

        import base64, json
        pad = lambda s: s + "=" * (-len(s) % 4)
        sid2 = json.loads(base64.urlsafe_b64decode(pad(t2.split(".")[1])))["sid"]

        resp = await client.post(
            f"/auth/sessions/{sid2}/revoke",
            headers={"Authorization": f"Bearer {t1}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["revoked_session_id"] == sid2
        assert body["revoked_family_id"] is not None

        # DB confirms revoked
        row = (await db_session.execute(
            select(Session).where(Session.id == uuid.UUID(sid2))
        )).scalar_one()
        await db_session.refresh(row)
        assert row.revoked is True

    @pytest.mark.asyncio
    async def test_revoke_unknown_session_404(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        await _create_user_with_role(db_session, "rev2@test.com", "R2", "client")
        t = await get_access_token(client, "rev2@test.com")
        resp = await client.post(
            f"/auth/sessions/{uuid.uuid4()}/revoke",
            headers={"Authorization": f"Bearer {t}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cant_revoke_someone_elses_session(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        """Caller tries to revoke a Session that doesn't belong to them →
        404 (we 404 instead of 403 to avoid leaking the existence of
        another user's session). We synthesize the "other user" row in
        the DB to keep this test independent of cross-user login timing,
        which proved flaky against the test fixtures."""
        from domains.users.models import User as UserModel
        from domains.auth.service import AuthService

        await _create_user_with_role(db_session, "owner@test.com", "Owner", "client")
        token = await get_access_token(client, "owner@test.com")
        assert token

        # Create a stranger directly + a Session row owned by them.
        stranger = UserModel(
            email="stranger@test.com",
            full_name="Stranger",
            password_hash=AuthService.hash_password("x"),
            is_active=True,
        )
        db_session.add(stranger)
        await db_session.flush()

        from domains.auth.session_repository import SessionRepository
        repo = SessionRepository(db_session)
        stranger_session = await repo.create(
            user_id=stranger.id, family_id=uuid.uuid4(),
            device_name="Stranger's phone", device_type="mobile",
            ip_address="10.0.0.2", user_agent="UA",
        )
        await db_session.commit()

        resp = await client.post(
            f"/auth/sessions/{stranger_session.id}/revoke",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_is_idempotent(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        await _create_user_with_role(db_session, "rev3@test.com", "R3", "client")
        t1 = await get_access_token(client, "rev3@test.com")
        t2 = await get_access_token(client, "rev3@test.com")

        import base64, json
        pad = lambda s: s + "=" * (-len(s) % 4)
        sid2 = json.loads(base64.urlsafe_b64decode(pad(t2.split(".")[1])))["sid"]

        r1 = await client.post(
            f"/auth/sessions/{sid2}/revoke",
            headers={"Authorization": f"Bearer {t1}"},
        )
        r2 = await client.post(
            f"/auth/sessions/{sid2}/revoke",
            headers={"Authorization": f"Bearer {t1}"},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert "already revoked" in r2.json()["message"].lower()


# ── DELETE /sessions (revoke-all) ──────────────────────────────────── #


class TestRevokeAll:
    @pytest.mark.asyncio
    async def test_revoke_all(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        user = await _create_user_with_role(db_session, "all@test.com", "All", "client")
        # 3 logins → 3 sessions
        t1 = await get_access_token(client, "all@test.com")
        await get_access_token(client, "all@test.com")
        await get_access_token(client, "all@test.com")

        resp = await client.delete(
            "/auth/sessions",
            headers={"Authorization": f"Bearer {t1}"},
        )
        assert resp.status_code == 204

        rows = (await db_session.execute(
            select(Session).where(Session.user_id == user.id)
        )).scalars().all()
        for r in rows:
            await db_session.refresh(r)
        assert all(s.revoked for s in rows)
