"""
tests/test_users_avatar.py — Avatar + cover upload flow (Phase 2 chunk K).

Each test runs the full register → complete-profile → login dance to mint
a client token, then exercises the avatar endpoints. Tests use the
LocalStorageAdapter so the entire flow (presigned URL, /dev/upload, HEAD,
confirm) runs against the local filesystem under ./storage/.

Cleanup is best-effort — `tmp_path` would be cleaner but the
LocalStorageAdapter's BASE_PATH is module-level. We just leave files
behind for the test run.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from httpx import AsyncClient


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login_as_client(client: AsyncClient, email: str) -> str:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201, reg.text
    onboarding = reg.json()["onboarding_token"]

    await client.put(
        "/auth/complete-profile",
        json={"full_name": "Avatar Tester", "phone_number": "+15551234567"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )

    login = await client.post(
        "/auth/login",
        json={"email": email, "password": "Secure1234!"},
    )
    return login.json()["access_token"]


def _png_bytes(width: int = 4, height: int = 4) -> bytes:
    """Build the smallest possible PNG so /dev/upload accepts the mime."""
    # 1×1 black PNG — the four-byte size override comes from the IHDR chunk.
    return bytes.fromhex(
        "89504e470d0a1a0a"  # signature
        "0000000d49484452"  # IHDR len + tag
        "0000000100000001080600000000"
        "1f15c4890000000d49444154"
        "78da63000100000005000100"
        "0d0a2db40000000049454e44"
        "ae426082"
    )


# ─── /avatar/upload-url ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_avatar_upload_url_returns_presigned(client: AsyncClient) -> None:
    token = await _login_as_client(client, "avatar-url@test.com")

    resp = await client.post(
        "/api/v1/users/me/avatar/upload-url",
        json={"mime_type": "image/png", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["url"].startswith("/dev/upload")
    assert data["method"] in {"POST", "PUT"}
    assert data["headers"]["Content-Type"] == "image/png"
    assert data["s3_key"].startswith("avatars/")
    assert data["expires_in"] >= 60


@pytest.mark.asyncio
async def test_avatar_upload_url_rejects_invalid_mime(client: AsyncClient) -> None:
    token = await _login_as_client(client, "avatar-badmime@test.com")
    resp = await client.post(
        "/api/v1/users/me/avatar/upload-url",
        json={"mime_type": "application/pdf", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "validation_failed"


@pytest.mark.asyncio
async def test_avatar_upload_url_rejects_oversized(client: AsyncClient) -> None:
    token = await _login_as_client(client, "avatar-toobig@test.com")
    resp = await client.post(
        "/api/v1/users/me/avatar/upload-url",
        json={"mime_type": "image/png", "size_bytes": 50 * 1024 * 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text


# ─── full flow: upload-url → /dev/upload → confirm ───────────────────────────


@pytest.mark.asyncio
async def test_avatar_full_flow_persists_key_on_user(client: AsyncClient) -> None:
    token = await _login_as_client(client, "avatar-flow@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. presigned URL
    body = _png_bytes()
    url_resp = await client.post(
        "/api/v1/users/me/avatar/upload-url",
        json={"mime_type": "image/png", "size_bytes": len(body)},
        headers=headers,
    )
    presigned = url_resp.json()["data"]
    s3_key = presigned["s3_key"]

    # 2. PUT the bytes (LocalStorageAdapter exposes this as POST /dev/upload)
    put_resp = await client.request(
        presigned["method"],
        presigned["url"],
        content=body,
        headers={"Content-Type": "image/png"},
    )
    assert put_resp.status_code == 200, put_resp.text

    # 3. confirm
    confirm = await client.post(
        "/api/v1/users/me/avatar",
        json={"s3_key": s3_key},
        headers=headers,
    )
    assert confirm.status_code == 200, confirm.text
    data = confirm.json()["data"]
    assert data["avatar_url"] is not None
    assert data["avatar_url"].startswith("/storage/")

    # 4. Hub reflects the new avatar_url.
    me_resp = await client.get(
        "/api/v1/users/me?include=profile",
        headers=headers,
    )
    profile = me_resp.json()["data"]["profile"]
    assert profile["avatar_url"] is not None
    assert profile["avatar_url"].endswith(re.sub(r".*?/", "", s3_key).rsplit("/", 1)[-1])


# ─── confirm rejects forged s3_key ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_avatar_confirm_rejects_foreign_key(client: AsyncClient) -> None:
    token = await _login_as_client(client, "avatar-foreign@test.com")
    resp = await client.post(
        "/api/v1/users/me/avatar",
        json={"s3_key": "avatars/00000000-0000-0000-0000-000000000000/abc.png"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "permission_denied"


# ─── confirm 404 when the upload never landed ────────────────────────────────


@pytest.mark.asyncio
async def test_avatar_confirm_404_when_no_object(client: AsyncClient) -> None:
    token = await _login_as_client(client, "avatar-missing@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    url_resp = await client.post(
        "/api/v1/users/me/avatar/upload-url",
        json={"mime_type": "image/png", "size_bytes": 256},
        headers=headers,
    )
    s3_key = url_resp.json()["data"]["s3_key"]
    # Skip the PUT — the object never lands.
    confirm = await client.post(
        "/api/v1/users/me/avatar",
        json={"s3_key": s3_key},
        headers=headers,
    )
    assert confirm.status_code == 404, confirm.text
    assert confirm.json()["error"]["code"] == "resource_not_found"


# ─── DELETE clears the column ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_avatar_delete_clears_column(client: AsyncClient) -> None:
    token = await _login_as_client(client, "avatar-del@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    body = _png_bytes()
    url_resp = await client.post(
        "/api/v1/users/me/avatar/upload-url",
        json={"mime_type": "image/png", "size_bytes": len(body)},
        headers=headers,
    )
    p = url_resp.json()["data"]
    await client.request(p["method"], p["url"], content=body, headers={"Content-Type": "image/png"})
    await client.post(
        "/api/v1/users/me/avatar",
        json={"s3_key": p["s3_key"]},
        headers=headers,
    )

    # Confirm DELETE returns 204 and the Hub stops surfacing the avatar.
    del_resp = await client.delete("/api/v1/users/me/avatar", headers=headers)
    assert del_resp.status_code == 204, del_resp.text

    me_resp = await client.get(
        "/api/v1/users/me?include=profile",
        headers=headers,
    )
    assert me_resp.json()["data"]["profile"]["avatar_url"] is None


# ─── /cover is gated to detailers ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cover_endpoint_rejects_clients(client: AsyncClient) -> None:
    token = await _login_as_client(client, "cover-client@test.com")
    resp = await client.post(
        "/api/v1/users/me/cover/upload-url",
        json={"mime_type": "image/png", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "permission_denied"
