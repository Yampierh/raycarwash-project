"""
tests/test_session_enforcement.py — Plan 23 Fase 1 día 2-3.

Covers the stateful-session layer that sits on top of the JWT:

  - Login flow emits `sid` claim + persists a Session row
  - The Session row has IP + user_agent populated from the request
  - get_current_user enforces revocation when AUTH_ENFORCE_SESSION=True
  - Cold cache + revoked session → 401
  - Refresh flow keeps the same Session (same family_id)
  - Old tokens without `sid` are still accepted (backwards compat)
"""
from __future__ import annotations

import base64
import json
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from domains.auth.models import Session
from domains.auth.service import AuthService
from tests.conftest import _create_user_with_role, get_access_token


def _decode_payload(token: str) -> dict:
    parts = token.split(".")
    pad = lambda s: s + "=" * (-len(s) % 4)
    return json.loads(base64.urlsafe_b64decode(pad(parts[1])))


async def _login_get_token_and_sid(
    client: AsyncClient, db: AsyncSession, email: str,
) -> tuple[str, str]:
    await _create_user_with_role(db, email, "User " + email, "client")
    token = await get_access_token(client, email)
    payload = _decode_payload(token)
    return token, payload.get("sid", "")


# ── Token claim + persistence ──────────────────────────────────────── #


class TestLoginEmitsSid:
    @pytest.mark.asyncio
    async def test_token_carries_sid(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        token, sid = await _login_get_token_and_sid(client, db_session, "sid-1@test.com")
        assert sid, "access token must include `sid` after Plan 23 Fase 1 día 3"
        assert uuid.UUID(sid)  # parseable

    @pytest.mark.asyncio
    async def test_session_row_created(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        _, sid = await _login_get_token_and_sid(client, db_session, "sid-2@test.com")
        row = (await db_session.execute(
            select(Session).where(Session.id == uuid.UUID(sid))
        )).scalar_one()
        assert row.revoked is False
        assert row.user_agent is not None

    @pytest.mark.asyncio
    async def test_old_token_without_sid_still_accepted(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        """Backwards compatibility: tokens minted before Fase 1 día 3 have
        no `sid` claim. With AUTH_ENFORCE_SESSION=False (default), they
        keep working — the enforce block is skipped."""
        user = await _create_user_with_role(db_session, "legacy@test.com", "Legacy", "client")
        # Mint a token without session_id — what pre-rollout code emitted.
        legacy_token = AuthService.create_access_token(
            subject=user.id, role_name="client", token_version=user.token_version,
        )
        payload = _decode_payload(legacy_token)
        assert "sid" not in payload  # confirm no sid in the legacy token

        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {legacy_token}"},
        )
        assert resp.status_code == 200


# ── Enforce flag ───────────────────────────────────────────────────── #


class TestEnforceFlag:
    @pytest.mark.asyncio
    async def test_revoked_session_rejected_when_enforced(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch,
    ):
        """With AUTH_ENFORCE_SESSION=True and the cached session marked
        revoked, the request is rejected even though the JWT signature
        is still valid."""
        # Flip the flag for this test only.
        settings = get_settings()
        monkeypatch.setattr(settings, "AUTH_ENFORCE_SESSION", True)

        token, sid = await _login_get_token_and_sid(
            client, db_session, "revoked@test.com",
        )
        # First request succeeds + populates cache as not-revoked.
        ok = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert ok.status_code == 200

        # Revoke in DB and evict cache so the next request reads fresh.
        from domains.auth.session_repository import SessionRepository
        from domains.auth.service import invalidate_session_cache

        repo = SessionRepository(db_session)
        revoked = await repo.revoke(uuid.UUID(sid))
        assert revoked
        await db_session.commit()

        # Evict the cache through the same redis the app uses.
        # The test client's app exposes its redis at app.state.redis.
        redis_client = client._transport.app.state.redis  # type: ignore[attr-defined]
        await invalidate_session_cache(sid, redis_client)

        denied = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert denied.status_code == 401

    @pytest.mark.asyncio
    async def test_unenforced_revoked_session_still_passes(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        """With the default AUTH_ENFORCE_SESSION=False, revoking a session
        in DB does NOT 401 the request. Confirms the flag actually gates
        the enforcement code path (otherwise rollout would break legacy
        tokens immediately)."""
        token, sid = await _login_get_token_and_sid(
            client, db_session, "noenf@test.com",
        )
        from domains.auth.session_repository import SessionRepository

        repo = SessionRepository(db_session)
        await repo.revoke(uuid.UUID(sid))
        await db_session.commit()

        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


# ── Refresh keeps session ──────────────────────────────────────────── #


class TestRefreshKeepsSession:
    @pytest.mark.asyncio
    async def test_refresh_reuses_same_sid(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        """Refresh-token rotation MUST keep the same `sid` — same family
        = same session. A new sid would mean every refresh creates a
        new Session row, which defeats the whole device-listing UX."""
        email = "refresh@test.com"
        await _create_user_with_role(db_session, email, "Ref", "client")

        # Login (regular password flow returns refresh + access tokens)
        r = await client.post(
            "/auth/token",
            data={"username": email, "password": "Test1234!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = r.json()
        access1 = body["access_token"]
        refresh1 = body["refresh_token"]
        sid1 = _decode_payload(access1)["sid"]

        # Rotate (the endpoint takes refresh_token as a query param)
        r2 = await client.post(f"/auth/refresh?refresh_token={refresh1}")
        assert r2.status_code == 200
        access2 = r2.json()["access_token"]
        sid2 = _decode_payload(access2)["sid"]

        assert sid1 == sid2, "refresh must preserve the session id"
