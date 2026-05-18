"""
tests/test_step_up_wiring.py — Hotfix H3 (the critical one).

Before this hotfix, ``mark_step_up()`` existed in ``app/core/step_up.py``
but was never invoked from production code. Every step-up-gated endpoint
shipped in Phase 3 (security summary, sessions, 2FA, contact change)
silently 401'd every real user immediately after they logged in. The
existing unit tests passed only because they called ``mark_step_up()``
manually inside fixtures.

This module enforces the contract that an end-to-end auth flow leaves
the step-up window OPEN. Each test would have failed before H3.

Concretely:
  - After ``POST /auth/login`` the user can immediately
    ``GET /users/me?include=security,sessions`` without a step-up bounce.
  - After ``POST /auth/token`` (OAuth2 password) the same holds.
  - After ``POST /auth/identify`` with a password the same holds.
  - ``POST /auth/refresh`` does NOT extend the step-up window — refresh
    is "still authenticated", not "re-authenticated".

The 6th and 7th auth sites (OAuth Google/Apple, WebAuthn complete) wire
``record_step_up_success`` identically; we don't replay the full OAuth
ceremony in unit tests, but the wiring is identical and visible in the
router diff.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from domains.users.models import User


async def _register_and_login(client: AsyncClient, email: str) -> tuple[str, str]:
    """Register a new user, complete onboarding, log in, return tokens."""
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "ValidPass123!", "intent_role": "client"},
    )
    assert reg.status_code in (200, 201), reg.text
    onboarding = reg.json()["onboarding_token"]

    completed = await client.put(
        "/auth/complete-profile",
        json={"full_name": "Step Up"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    assert completed.status_code == 200, completed.text

    login = await client.post(
        "/auth/login",
        json={"email": email, "password": "ValidPass123!"},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    return body["access_token"], body["refresh_token"]


@pytest.mark.asyncio
async def test_login_opens_step_up_window_for_hub_security_block(
    client: AsyncClient, db_session: AsyncSession
):
    """The smoke test the team should have written months ago."""
    access, _refresh = await _register_and_login(client, "stepup-login@test.com")

    resp = await client.get(
        "/api/v1/users/me?include=security,sessions",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200, (
        "POST /auth/login MUST populate last_step_up_at — pre-H3 this "
        "endpoint silently 401'd every real user with step_up_required. "
        "Response: %s" % resp.text
    )
    body = resp.json()
    includes = body["meta"].get("includes") or []
    assert "security" in includes
    assert "sessions" in includes
    assert body["data"]["security"] is not None


@pytest.mark.asyncio
async def test_login_persists_last_step_up_at_on_user_row(
    client: AsyncClient, db_session: AsyncSession
):
    """DB-level evidence: the column is populated, not just Redis."""
    email = "stepup-dbcolumn@test.com"
    await _register_and_login(client, email)

    user = (
        await db_session.execute(
            select(User).where(User.email == email)
        )
    ).scalar_one()
    assert user.last_step_up_at is not None
    delta = datetime.now(timezone.utc) - user.last_step_up_at
    assert delta < timedelta(minutes=1), (
        "last_step_up_at should be within seconds of the login call"
    )


@pytest.mark.asyncio
async def test_oauth2_token_endpoint_opens_step_up_window(
    client: AsyncClient, db_session: AsyncSession
):
    """OAuth2 Password Flow (Swagger compatibility) — same auth event class
    as /auth/login, must populate step-up identically."""
    email = "stepup-oauth2@test.com"
    await _register_and_login(client, email)

    # Reset step-up by clearing the column directly.
    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    user.last_step_up_at = None
    await db_session.commit()

    token_resp = await client.post(
        "/auth/token",
        data={"username": email, "password": "ValidPass123!"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200, token_resp.text
    access = token_resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/users/me?include=security",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_identify_with_password_opens_step_up_window(
    client: AsyncClient, db_session: AsyncSession
):
    """The Identifier-First /auth/verify path with password is also a
    real auth event and must populate step-up."""
    email = "stepup-identify@test.com"
    await _register_and_login(client, email)

    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    user.last_step_up_at = None
    await db_session.commit()

    verify = await client.post(
        "/auth/verify",
        json={
            "identifier": email,
            "identifier_type": "email",
            "password": "ValidPass123!",
        },
    )
    assert verify.status_code == 200, verify.text
    access = verify.json()["access_token"]
    assert access is not None

    resp = await client.get(
        "/api/v1/users/me?include=security",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_refresh_does_NOT_extend_step_up_window(
    client: AsyncClient, db_session: AsyncSession
):
    """Refresh is "still authenticated", not "re-authenticated".

    If refresh extended step-up, a stolen refresh token would bypass
    every step-up wall forever. This test pins the boundary: after
    explicitly expiring the step-up window, a refresh restores the
    access token but MUST NOT restore the step-up window.
    """
    email = "stepup-refresh@test.com"
    _access, refresh = await _register_and_login(client, email)

    # Push the step-up timestamp outside the window (the user's last real
    # auth was a long time ago — they've been on auto-refresh ever since).
    settings = get_settings()
    user = (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()
    user.last_step_up_at = datetime.now(timezone.utc) - timedelta(
        minutes=settings.STEP_UP_TTL_MINUTES + 5
    )
    await db_session.commit()

    refresh_resp = await client.post(
        "/auth/refresh",
        params={"refresh_token": refresh},
    )
    assert refresh_resp.status_code == 200, refresh_resp.text
    new_access = refresh_resp.json()["access_token"]

    # The refreshed user can still hit non-sensitive endpoints…
    profile_resp = await client.get(
        "/api/v1/users/me?include=profile",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert profile_resp.status_code == 200, profile_resp.text

    # …but sensitive includes MUST 401 step_up_required: the user has not
    # re-authenticated, only refreshed.
    sensitive = await client.get(
        "/api/v1/users/me?include=security",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert sensitive.status_code == 401, (
        "/auth/refresh extended the step-up window — that would let "
        "stolen refresh tokens bypass step-up walls indefinitely. "
        "Response: %s" % sensitive.text
    )
    assert sensitive.json()["error"]["code"] == "step_up_required"

    # And the DB column was NOT bumped by the refresh.
    await db_session.refresh(user)
    delta = datetime.now(timezone.utc) - user.last_step_up_at
    assert delta > timedelta(minutes=settings.STEP_UP_TTL_MINUTES), (
        "last_step_up_at was modified by /auth/refresh — this violates the "
        "step-up boundary contract."
    )
