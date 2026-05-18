"""
tests/test_users_vehicle_photos.py — Phase 4 chunk V (vehicle photos).

The LocalStorageAdapter is used end-to-end: tests POST to /dev/upload
to materialize bytes on disk so HEAD / size / content-type checks
exercise real adapter code rather than mocks.
"""
from __future__ import annotations

import io
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.users.models import User
from domains.vehicles.models import Vehicle


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str = "veh-photo@test.com") -> str:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201
    onboarding = reg.json()["onboarding_token"]
    phone_suffix = str(abs(hash(email)) % 10_000_000).zfill(7)
    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Veh Tester", "phone_number": f"+155{phone_suffix}"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Secure1234!"},
    )
    return login.json()["access_token"]


async def _create_vehicle(
    client: AsyncClient, token: str
) -> str:
    resp = await client.post(
        "/api/v1/vehicles",
        json={
            "make": "Toyota",
            "model": "Camry",
            "year": 2022,
            "color": "blue",
            "license_plate": f"PLT{uuid.uuid4().hex[:5].upper()}",
            "body_class": "Sedan",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


async def _upload_photo(
    client: AsyncClient, token: str, vehicle_id: str, caption: str | None = None
) -> dict:
    """Drive the full two-step flow: request URL → PUT bytes via /dev/
    upload → confirm. Returns the confirm response data."""
    url_resp = await client.post(
        f"/api/v1/users/me/vehicles/{vehicle_id}/photos/upload-url",
        json={"mime_type": "image/jpeg", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert url_resp.status_code == 200, url_resp.text
    presigned = url_resp.json()["data"]

    # LocalStorageAdapter exposes /dev/upload with an HMAC signature
    # baked into the presigned URL. Just POST the bytes there.
    bytes_payload = b"\xff\xd8\xff" + b"x" * 1021  # tiny JPEG-ish blob
    put_resp = await client.post(
        presigned["url"],
        content=bytes_payload,
        headers={"Content-Type": "image/jpeg"},
    )
    assert put_resp.status_code in (200, 201, 204), put_resp.text

    confirm = await client.post(
        f"/api/v1/users/me/vehicles/{vehicle_id}/photos",
        json={"s3_key": presigned["s3_key"], "caption": caption},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm.status_code == 201, confirm.text
    return confirm.json()["data"]


# ─── Upload flow ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_two_step_upload_creates_photo_row(
    client: AsyncClient,
) -> None:
    token = await _login(client, "veh-flow@test.com")
    veh_id = await _create_vehicle(client, token)

    photo = await _upload_photo(client, token, veh_id, caption="Front quarter")
    assert photo["vehicle_id"] == veh_id
    assert photo["caption"] == "Front quarter"
    assert photo["sort_order"] == 0
    assert photo["photo_url"]


@pytest.mark.asyncio
async def test_listing_orders_by_sort_order(
    client: AsyncClient,
) -> None:
    token = await _login(client, "veh-order@test.com")
    veh_id = await _create_vehicle(client, token)

    p1 = await _upload_photo(client, token, veh_id, "first")
    p2 = await _upload_photo(client, token, veh_id, "second")

    listing = await client.get(
        f"/api/v1/users/me/vehicles/{veh_id}/photos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.status_code == 200, listing.text
    items = listing.json()["data"]
    assert [i["caption"] for i in items] == ["first", "second"]
    assert items[0]["sort_order"] == 0
    assert items[1]["sort_order"] == 1


@pytest.mark.asyncio
async def test_photo_cap_blocks_fifth_upload(
    client: AsyncClient,
) -> None:
    token = await _login(client, "veh-cap@test.com")
    veh_id = await _create_vehicle(client, token)

    # Cap is 4.
    for i in range(4):
        await _upload_photo(client, token, veh_id, f"photo {i}")

    # 5th upload-url request must be rejected BEFORE we waste bytes.
    resp = await client.post(
        f"/api/v1/users/me/vehicles/{veh_id}/photos/upload-url",
        json={"mime_type": "image/jpeg", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["code"] == "conflict"


# ─── Ownership + s3_key spoofing ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_user_vehicle_returns_404(
    client: AsyncClient,
) -> None:
    alice = await _login(client, "veh-alice@test.com")
    bob = await _login(client, "veh-bob@test.com")
    alice_veh = await _create_vehicle(client, alice)

    # Bob requests an upload URL for Alice's vehicle.
    resp = await client.post(
        f"/api/v1/users/me/vehicles/{alice_veh}/photos/upload-url",
        json={"mime_type": "image/jpeg", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {bob}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_confirm_with_spoofed_s3_key_returns_403(
    client: AsyncClient,
) -> None:
    """The s3_key must start with vehicle_photos/{vehicle_id}/ —
    without that anti-spoof check a client could confirm any object
    in the public bucket and bind it to their vehicle."""
    token = await _login(client, "veh-spoof@test.com")
    veh_id = await _create_vehicle(client, token)

    confirm = await client.post(
        f"/api/v1/users/me/vehicles/{veh_id}/photos",
        json={"s3_key": "avatars/12345/foo.jpg", "caption": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm.status_code == 403
    assert confirm.json()["error"]["code"] == "permission_denied"


# ─── Delete ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_photo_removes_row(
    client: AsyncClient,
) -> None:
    token = await _login(client, "veh-del@test.com")
    veh_id = await _create_vehicle(client, token)
    photo = await _upload_photo(client, token, veh_id, "trash me")

    resp = await client.delete(
        f"/api/v1/users/me/vehicles/{veh_id}/photos/{photo['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    listing = await client.get(
        f"/api/v1/users/me/vehicles/{veh_id}/photos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.json()["data"] == []


# ─── Hub vehicles block carries the first-photo URL ──────────────────────────


@pytest.mark.asyncio
async def test_hub_vehicles_block_carries_first_photo_url(
    client: AsyncClient,
) -> None:
    token = await _login(client, "veh-hub@test.com")
    veh_id = await _create_vehicle(client, token)
    first = await _upload_photo(client, token, veh_id, "lead")
    await _upload_photo(client, token, veh_id, "secondary")

    resp = await client.get(
        "/api/v1/users/me?include=vehicles",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    vehicles = resp.json()["data"]["vehicles"]
    assert len(vehicles) == 1
    # The Hub must surface the lead photo (sort_order=0).
    assert vehicles[0]["photo_url"]
    assert "vehicle_photos/" in vehicles[0]["photo_url"]
