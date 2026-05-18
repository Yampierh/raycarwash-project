"""
tests/test_users_hub.py — End-to-end coverage for GET/PATCH /api/v1/users/me
(ADR-002b — Profile Hub).

Each test runs against a real PostgreSQL (via the test_db fixture in
conftest.py). Helper `_login_as_client` performs the full
register → complete-profile → login dance and returns the access token.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login_as_client(client: AsyncClient, email: str = "hub@test.com") -> str:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201, reg.text
    onboarding = reg.json()["onboarding_token"]

    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Hub Test User", "phone_number": "+15551234567"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )

    login = await client.post(
        "/auth/login",
        json={"email": email, "password": "Secure1234!"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _envelope(resp_json: dict) -> dict:
    """Hub responses are wrapped in `{data, meta, links}` — unwrap `data`."""
    assert "data" in resp_json, f"missing data: {resp_json}"
    return resp_json["data"]


# ─── GET /users/me — defaults ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hub_default_returns_only_user_and_badges(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-default@test.com")

    resp = await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    data = _envelope(body)

    assert data["user"]["email"] == "hub-default@test.com"
    assert data["verification_badges"]["email"] is False
    assert data["verification_badges"]["identity"] is False
    # No include= → everything else is None.
    assert data["profile"] is None
    assert data["stats"] is None
    assert data["security"] is None
    assert data["sessions"] is None
    assert data["provider"] is None
    assert data["vehicles"] is None

    assert body["meta"]["includes"] is None or body["meta"]["includes"] == []


# ─── GET /users/me?include=profile,stats ──────────────────────────────────────


@pytest.mark.asyncio
async def test_hub_profile_and_stats_block_populated(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-profile@test.com")

    resp = await client.get(
        "/api/v1/users/me?include=profile,stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    data = _envelope(body)

    assert data["profile"] is not None
    assert data["profile"]["full_name"] == "Hub Test User"
    assert data["profile"]["first_name"] == "Hub"
    assert data["profile"]["last_name"] == "Test User"
    assert data["profile"]["language"] == "en"

    assert data["stats"] is not None
    assert data["stats"]["total_bookings"] == 0
    assert data["stats"]["vehicles_total"] == 0

    assert sorted(body["meta"]["includes"]) == ["profile", "stats"]


# ─── GET /users/me?include=security,sessions without step-up ─────────────────


@pytest.mark.asyncio
async def test_hub_sensitive_after_step_up_expires_returns_401_step_up_required(
    client: AsyncClient,
    db_session,
) -> None:
    """Post-Hotfix H3, /auth/login bumps last_step_up_at so the user can
    immediately hit ?include=security. To exercise the rejection path
    we explicitly expire the column."""
    from sqlalchemy import update
    from domains.users.models import User

    token = await _login_as_client(client, "hub-stepup@test.com")
    await db_session.execute(
        update(User)
        .where(User.email == "hub-stepup@test.com")
        .values(last_step_up_at=None)
    )
    await db_session.commit()

    resp = await client.get(
        "/api/v1/users/me?include=security",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["error"]["code"] == "step_up_required"
    assert "security" in body["meta"]["requires_step_up"]


# ─── GET /users/me?include=security&on_step_up=skip ──────────────────────────


@pytest.mark.asyncio
async def test_hub_skip_step_up_returns_200_with_skipped_marker(
    client: AsyncClient,
) -> None:
    token = await _login_as_client(client, "hub-skip@test.com")

    resp = await client.get(
        "/api/v1/users/me?include=profile,security&on_step_up=skip",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    data = _envelope(body)

    # profile always lands; security may or may not depending on step-up state.
    assert data["profile"] is not None
    includes = body["meta"].get("includes") or []
    skipped = body["meta"].get("skipped_due_to_step_up") or []
    assert "security" in includes or "security" in skipped


# ─── GET /users/me?include=garbage ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hub_unknown_token_returns_400(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-bad@test.com")

    resp = await client.get(
        "/api/v1/users/me?include=garbage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["error"]["code"] == "bad_request"


# ─── GET /users/me?include=provider as a pure client → silently omitted ──────


@pytest.mark.asyncio
async def test_hub_provider_token_silently_dropped_for_clients(
    client: AsyncClient,
) -> None:
    token = await _login_as_client(client, "hub-clientonly@test.com")

    resp = await client.get(
        "/api/v1/users/me?include=provider,profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    data = _envelope(body)
    assert data["profile"] is not None
    # provider was dropped because the caller is not a detailer.
    assert data["provider"] is None
    assert "provider" not in (body["meta"].get("includes") or [])


# ─── PATCH /users/me updates profile block ────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_me_updates_first_name(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-patch@test.com")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"first_name": "Patched", "language": "es"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    data = _envelope(body)
    # PATCH returns profile + stats included.
    assert data["profile"]["first_name"] == "Patched"
    assert data["profile"]["language"] == "es"
    # The user's full_name should now start with "Patched".
    assert data["profile"]["full_name"].startswith("Patched ")


# ─── PATCH /users/me rejects bad language code ───────────────────────────────


@pytest.mark.asyncio
async def test_patch_me_rejects_invalid_language_tag(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-badlang@test.com")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"language": "ENGLISH"},  # not BCP-47
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["error"]["code"] == "validation_failed"


# ─── unauthenticated request returns 401 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_hub_unauthenticated_returns_401(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401, resp.text


# ─── E0 (00-user.md) — zip_code in profile block ──────────────────────────────


@pytest.mark.asyncio
async def test_hub_profile_returns_null_zipcode_by_default(
    client: AsyncClient,
) -> None:
    token = await _login_as_client(client, "hub-zip-default@test.com")

    resp = await client.get(
        "/api/v1/users/me?include=profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = _envelope(resp.json())
    assert "zip_code" in data["profile"]
    assert data["profile"]["zip_code"] is None


@pytest.mark.asyncio
async def test_patch_me_sets_zip_code(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-zip-set@test.com")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"zip_code": "46802"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = _envelope(resp.json())
    assert data["profile"]["zip_code"] == "46802"


@pytest.mark.asyncio
async def test_patch_me_supports_zip_plus_four(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-zip-plus4@test.com")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"zip_code": "46802-1234"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = _envelope(resp.json())
    assert data["profile"]["zip_code"] == "46802-1234"


@pytest.mark.asyncio
async def test_patch_me_rejects_zip_too_short(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-zip-short@test.com")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"zip_code": "12"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["error"]["code"] == "validation_failed"


@pytest.mark.asyncio
async def test_patch_me_rejects_zip_too_long(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-zip-long@test.com")

    resp = await client.patch(
        "/api/v1/users/me",
        json={"zip_code": "1234567890123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_patch_me_preserves_zip_when_omitted(client: AsyncClient) -> None:
    token = await _login_as_client(client, "hub-zip-preserve@test.com")

    # Set it first.
    set_resp = await client.patch(
        "/api/v1/users/me",
        json={"zip_code": "46802"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert set_resp.status_code == 200

    # A patch that doesn't mention zip_code must not clear it.
    patch_resp = await client.patch(
        "/api/v1/users/me",
        json={"language": "es"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200, patch_resp.text
    data = _envelope(patch_resp.json())
    assert data["profile"]["zip_code"] == "46802"
    assert data["profile"]["language"] == "es"
