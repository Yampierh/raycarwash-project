"""
tests/test_users_contact_change.py — Email + phone change flows (Phase 3
chunk N).

Each test mints a fresh user via register → complete-profile → login,
then exercises the /users/me/email/* and /users/me/phone/* endpoints.
Email tokens and phone OTPs are surfaced via the `data.dev_token` field
because the test environment runs with RAYCARWASH_ENV=development.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.step_up import mark_step_up
from domains.users.models import User
from domains.users.pending_contact_change import PendingContactChange


# ─── fixtures / helpers ──────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str, password: str = "Secure1234!") -> str:
    reg = await client.post(
        "/auth/register", json={"email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    onboarding = reg.json()["onboarding_token"]

    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Contact Tester", "phone_number": "+15551110000"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )

    login = await client.post(
        "/auth/login", json={"email": email, "password": password},
    )
    return login.json()["access_token"]


async def _seed_step_up(db_session: AsyncSession, user_email: str) -> None:
    """Mark the user as step-up-recent so /change-request goes through.

    Historical note: pre-Hotfix H3, login NEVER bumped last_step_up_at
    (mark_step_up was never invoked from production code), so tests had
    to seed the column manually. Post-H3, login auto-populates it — but
    we keep this helper for tests that need to grant step-up to a user
    that was created without going through /auth/login (e.g. via fixture)."""
    now = datetime.now(timezone.utc)
    await db_session.execute(
        update(User).where(User.email == user_email).values(last_step_up_at=now)
    )
    await db_session.commit()


async def _expire_step_up(db_session: AsyncSession, user_email: str) -> None:
    """Push last_step_up_at to NULL so the next step-up-gated request 401s.
    Needed after H3 because /auth/login bumps the column automatically."""
    await db_session.execute(
        update(User).where(User.email == user_email).values(last_step_up_at=None)
    )
    await db_session.commit()


# ─── /email/change-request ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_email_change_request_returns_dev_token(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "email-req@test.com")
    await _seed_step_up(db_session, "email-req@test.com")

    resp = await client.post(
        "/api/v1/users/me/email/change-request",
        json={"new_email": "moved@test.com", "current_password": "Secure1234!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()["data"]
    assert data["accepted"] is True
    # Dev mode returns the raw token so tests can drive /change-confirm.
    assert data["dev_token"] is not None
    assert len(data["dev_token"]) >= 40


@pytest.mark.asyncio
async def test_email_change_request_rejects_bad_password(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    access = await _login(client, "email-badpw@test.com")
    await _seed_step_up(db_session, "email-badpw@test.com")

    resp = await client.post(
        "/api/v1/users/me/email/change-request",
        json={"new_email": "moved@test.com", "current_password": "WrongPass!1"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "permission_denied"


@pytest.mark.asyncio
async def test_email_change_request_blocks_without_step_up(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    access = await _login(client, "email-nostep@test.com")
    # Post-H3, /auth/login automatically populates last_step_up_at.
    # Expire it so this test still exercises the step-up rejection path.
    await _expire_step_up(db_session, "email-nostep@test.com")

    resp = await client.post(
        "/api/v1/users/me/email/change-request",
        json={"new_email": "moved@test.com", "current_password": "Secure1234!"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "step_up_required"


# ─── /email/change-confirm ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_email_change_full_flow_swaps_email(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    access = await _login(client, "email-flow@test.com")
    await _seed_step_up(db_session, "email-flow@test.com")

    req = await client.post(
        "/api/v1/users/me/email/change-request",
        json={"new_email": "newaddr@test.com", "current_password": "Secure1234!"},
        headers={"Authorization": f"Bearer {access}"},
    )
    dev_token = req.json()["data"]["dev_token"]
    assert dev_token

    confirm = await client.post(
        "/api/v1/users/me/email/change-confirm",
        json={"token": dev_token},
    )
    assert confirm.status_code == 200, confirm.text
    body = confirm.json()["data"]
    assert body["new_value_masked"] == "n***@test.com"
    assert body["sessions_invalidated"] is True

    # The old access token must now fail because token_version was bumped.
    me = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert me.status_code == 401, me.text


@pytest.mark.asyncio
async def test_email_change_confirm_rejects_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/users/me/email/change-confirm",
        json={"token": "this-token-does-not-exist-anywhere-1234567890"},
    )
    assert resp.status_code == 410, resp.text
    assert resp.json()["error"]["code"] == "gone"


@pytest.mark.asyncio
async def test_email_change_confirm_rejects_expired_token(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    access = await _login(client, "email-expired@test.com")
    await _seed_step_up(db_session, "email-expired@test.com")

    req = await client.post(
        "/api/v1/users/me/email/change-request",
        json={"new_email": "exp@test.com", "current_password": "Secure1234!"},
        headers={"Authorization": f"Bearer {access}"},
    )
    dev_token = req.json()["data"]["dev_token"]

    # Backdate the pending row.
    await db_session.execute(
        update(PendingContactChange).values(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=2)
        )
    )
    await db_session.commit()

    confirm = await client.post(
        "/api/v1/users/me/email/change-confirm",
        json={"token": dev_token},
    )
    assert confirm.status_code == 410, confirm.text
    assert "expired" in confirm.json()["error"]["message"].lower()


# ─── /phone/change-request + /phone/change-verify ────────────────────────────


@pytest.mark.asyncio
async def test_phone_change_full_flow(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    access = await _login(client, "phone-flow@test.com")
    await _seed_step_up(db_session, "phone-flow@test.com")

    req = await client.post(
        "/api/v1/users/me/phone/change-request",
        json={"new_phone": "+15559998888", "current_password": "Secure1234!"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert req.status_code == 202, req.text
    otp = req.json()["data"]["dev_token"]
    assert otp is not None and len(otp) == 6

    verify = await client.post(
        "/api/v1/users/me/phone/change-verify",
        json={"otp": otp},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert verify.status_code == 200, verify.text
    body = verify.json()["data"]
    assert body["new_value_masked"] == "***8888"


@pytest.mark.asyncio
async def test_phone_change_verify_rejects_bad_otp(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    access = await _login(client, "phone-bad@test.com")
    await _seed_step_up(db_session, "phone-bad@test.com")

    await client.post(
        "/api/v1/users/me/phone/change-request",
        json={"new_phone": "+15554443333", "current_password": "Secure1234!"},
        headers={"Authorization": f"Bearer {access}"},
    )

    verify = await client.post(
        "/api/v1/users/me/phone/change-verify",
        json={"otp": "000000"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert verify.status_code == 422, verify.text
    assert "remaining" in verify.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_phone_change_verify_locks_after_5_attempts(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    access = await _login(client, "phone-lock@test.com")
    await _seed_step_up(db_session, "phone-lock@test.com")

    await client.post(
        "/api/v1/users/me/phone/change-request",
        json={"new_phone": "+15557776666", "current_password": "Secure1234!"},
        headers={"Authorization": f"Bearer {access}"},
    )

    # Burn five wrong attempts.
    for _ in range(5):
        await client.post(
            "/api/v1/users/me/phone/change-verify",
            json={"otp": "000000"},
            headers={"Authorization": f"Bearer {access}"},
        )

    # Sixth attempt — row already deleted → 410, NOT 423 because the
    # service deletes the row when attempts >= 5 and the next lookup
    # finds nothing.
    final = await client.post(
        "/api/v1/users/me/phone/change-verify",
        json={"otp": "000000"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert final.status_code in (410, 423), final.text


@pytest.mark.asyncio
async def test_phone_change_request_rejects_invalid_phone_format(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    access = await _login(client, "phone-format@test.com")
    await _seed_step_up(db_session, "phone-format@test.com")

    resp = await client.post(
        "/api/v1/users/me/phone/change-request",
        json={"new_phone": "not-a-phone", "current_password": "Secure1234!"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 422, resp.text
