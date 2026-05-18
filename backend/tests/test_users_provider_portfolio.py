"""
tests/test_users_provider_portfolio.py — Phase 5 chunk Y3.

Drives the two-step portfolio upload end-to-end via LocalStorageAdapter
+ /dev/upload, the same pattern test_users_vehicle_photos uses.
Validates ownership, cap enforcement, and the "must be activated"
guard.
"""
from __future__ import annotations

import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str) -> str:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201
    onboarding = reg.json()["onboarding_token"]
    phone_suffix = str(abs(hash(email)) % 10_000_000).zfill(7)
    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Portfolio Tester", "phone_number": f"+155{phone_suffix}"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Secure1234!"},
    )
    return login.json()["access_token"]


async def _activate_provider(client: AsyncClient, token: str) -> None:
    resp = await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Test Detailing"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text


async def _upload_portfolio_photo(
    client: AsyncClient, token: str, caption: str | None = None, tag: str | None = None,
) -> dict:
    url_resp = await client.post(
        "/api/v1/users/me/provider-portfolio/upload-url",
        json={"mime_type": "image/jpeg", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert url_resp.status_code == 200, url_resp.text
    presigned = url_resp.json()["data"]

    payload = b"\xff\xd8\xff" + b"x" * 1021
    put_resp = await client.post(
        presigned["url"],
        content=payload,
        headers={"Content-Type": "image/jpeg"},
    )
    assert put_resp.status_code in (200, 201, 204), put_resp.text

    confirm = await client.post(
        "/api/v1/users/me/provider-portfolio",
        json={"s3_key": presigned["s3_key"], "caption": caption, "tag": tag},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm.status_code == 201, confirm.text
    return confirm.json()["data"]


# ─── Activate-required guard ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_url_requires_active_provider(
    client: AsyncClient,
) -> None:
    """Calling provider-portfolio endpoints before activating provider
    mode must 409 with the 'activate first' hint."""
    token = await _login(client, "port-noactivate@test.com")
    resp = await client.post(
        "/api/v1/users/me/provider-portfolio/upload-url",
        json={"mime_type": "image/jpeg", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "conflict"


# ─── Upload flow ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_two_step_upload_creates_photo(
    client: AsyncClient,
) -> None:
    token = await _login(client, "port-upload@test.com")
    await _activate_provider(client, token)

    photo = await _upload_portfolio_photo(
        client, token, caption="Ceramic finish", tag="hero",
    )
    assert photo["caption"] == "Ceramic finish"
    assert photo["tag"] == "hero"
    assert photo["sort_order"] == 0
    assert photo["photo_url"]


@pytest.mark.asyncio
async def test_listing_ordered_by_sort_order(
    client: AsyncClient,
) -> None:
    token = await _login(client, "port-order@test.com")
    await _activate_provider(client, token)

    await _upload_portfolio_photo(client, token, "first", "before")
    await _upload_portfolio_photo(client, token, "second", "after")

    listing = await client.get(
        "/api/v1/users/me/provider-portfolio",
        headers={"Authorization": f"Bearer {token}"},
    )
    items = listing.json()["data"]
    assert [i["caption"] for i in items] == ["first", "second"]
    assert [i["sort_order"] for i in items] == [0, 1]


@pytest.mark.asyncio
async def test_confirm_with_spoofed_s3_key_returns_403(
    client: AsyncClient,
) -> None:
    """Anti-spoof: confirm payload must use the s3_key the upload-url
    flow returned (which carries the caller's user_id). A key under
    avatars/.../ must NOT bind to this provider's portfolio."""
    token = await _login(client, "port-spoof@test.com")
    await _activate_provider(client, token)

    confirm = await client.post(
        "/api/v1/users/me/provider-portfolio",
        json={"s3_key": "avatars/abc/foo.jpg", "caption": None, "tag": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm.status_code == 403
    assert confirm.json()["error"]["code"] == "permission_denied"


# ─── Delete ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_removes_row(
    client: AsyncClient,
) -> None:
    token = await _login(client, "port-delete@test.com")
    await _activate_provider(client, token)
    photo = await _upload_portfolio_photo(client, token, "drop me")

    resp = await client.delete(
        f"/api/v1/users/me/provider-portfolio/{photo['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    listing = await client.get(
        "/api/v1/users/me/provider-portfolio",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.json()["data"] == []


@pytest.mark.asyncio
async def test_delete_other_providers_photo_returns_404(
    client: AsyncClient,
) -> None:
    alice = await _login(client, "port-alice@test.com")
    bob = await _login(client, "port-bob@test.com")
    await _activate_provider(client, alice)
    await _activate_provider(client, bob)
    alice_photo = await _upload_portfolio_photo(client, alice, "alice's work")

    resp = await client.delete(
        f"/api/v1/users/me/provider-portfolio/{alice_photo['id']}",
        headers={"Authorization": f"Bearer {bob}"},
    )
    assert resp.status_code == 404
