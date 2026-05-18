"""
tests/test_users_provider_documents.py — Phase 5 chunk Y4.

KYC document upload via the private bucket. Uses the same /dev/upload
sink as the public-bucket tests; LocalStorageAdapter handles both
buckets behind the FileStorageAdapter Protocol.
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.users.document import Document
from domains.users.models import User


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
        json={"full_name": "Doc Tester", "phone_number": f"+155{phone_suffix}"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Secure1234!"},
    )
    return login.json()["access_token"]


async def _activate(client: AsyncClient, token: str) -> None:
    resp = await client.post(
        "/api/v1/users/me/provider-profile",
        json={"business_name": "Doc Co"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text


async def _upload_doc(
    client: AsyncClient,
    token: str,
    *,
    doc_type: str = "insurance",
    title: str | None = "2026 GL policy",
    expires_at: str | None = "2027-05-01",
    mime: str = "application/pdf",
) -> dict:
    url_resp = await client.post(
        "/api/v1/users/me/provider-documents/upload-url",
        json={"type": doc_type, "mime_type": mime, "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert url_resp.status_code == 200, url_resp.text
    presigned = url_resp.json()["data"]

    payload = b"%PDF-1.4\n" + b"x" * 1015  # PDF-ish, 1024 bytes total
    put_resp = await client.post(
        presigned["url"],
        content=payload,
        headers={"Content-Type": mime},
    )
    assert put_resp.status_code in (200, 201, 204), put_resp.text

    body = {
        "s3_key": presigned["s3_key"],
        "type": doc_type,
        "title": title,
    }
    if expires_at:
        body["expires_at"] = expires_at
    confirm = await client.post(
        "/api/v1/users/me/provider-documents",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm.status_code == 201, confirm.text
    return confirm.json()["data"]


async def _expire_step_up(db_session: AsyncSession, email: str) -> None:
    user = (await db_session.execute(
        select(User).where(User.email == email)
    )).scalar_one()
    user.last_step_up_at = None
    await db_session.commit()


# ─── Activate-required guard ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_url_requires_provider_mode(
    client: AsyncClient,
) -> None:
    token = await _login(client, "doc-noactivate@test.com")
    resp = await client.post(
        "/api/v1/users/me/provider-documents/upload-url",
        json={"type": "insurance", "mime_type": "application/pdf", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409, resp.text


# ─── Upload + list ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upload_creates_document_with_expiry_and_signed_url(
    client: AsyncClient,
) -> None:
    token = await _login(client, "doc-upload@test.com")
    await _activate(client, token)

    doc = await _upload_doc(client, token)
    assert doc["type"] == "insurance"
    assert doc["title"] == "2026 GL policy"
    assert doc["expires_at"] == "2027-05-01"
    # Confirmed bytes via /dev/upload — the listing endpoint signs a
    # download URL pointing at /storage/private-docs/...
    assert doc["download_url"]
    assert "private-docs" in doc["download_url"]


@pytest.mark.asyncio
async def test_list_returns_freshly_signed_urls(
    client: AsyncClient,
) -> None:
    token = await _login(client, "doc-list@test.com")
    await _activate(client, token)
    await _upload_doc(client, token, doc_type="insurance")
    await _upload_doc(client, token, doc_type="business_license", title="LLC reg")

    listing = await client.get(
        "/api/v1/users/me/provider-documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.status_code == 200, listing.text
    items = listing.json()["data"]
    assert len(items) == 2
    for item in items:
        assert item["download_url"]


# ─── Validation ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_type_rejected_at_upload_url(
    client: AsyncClient,
) -> None:
    token = await _login(client, "doc-badtype@test.com")
    await _activate(client, token)
    resp = await client.post(
        "/api/v1/users/me/provider-documents/upload-url",
        json={"type": "passport", "mime_type": "application/pdf", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_invalid_mime_rejected_at_upload_url(
    client: AsyncClient,
) -> None:
    token = await _login(client, "doc-badmime@test.com")
    await _activate(client, token)
    resp = await client.post(
        "/api/v1/users/me/provider-documents/upload-url",
        json={"type": "insurance", "mime_type": "text/plain", "size_bytes": 1024},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_confirm_with_spoofed_s3_key_returns_403(
    client: AsyncClient,
) -> None:
    token = await _login(client, "doc-spoof@test.com")
    await _activate(client, token)
    confirm = await client.post(
        "/api/v1/users/me/provider-documents",
        json={
            "s3_key": "avatars/abc/foo.pdf",
            "type": "insurance",
            "title": "spoofed",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm.status_code == 403


# ─── Delete + step-up ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_requires_step_up(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "doc-delnostep@test.com")
    await _activate(client, token)
    doc = await _upload_doc(client, token)

    await _expire_step_up(db_session, "doc-delnostep@test.com")

    resp = await client.delete(
        f"/api/v1/users/me/provider-documents/{doc['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "step_up_required"


@pytest.mark.asyncio
async def test_delete_soft_deletes_row_and_drops_listing(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    token = await _login(client, "doc-delok@test.com")
    await _activate(client, token)
    doc = await _upload_doc(client, token)

    resp = await client.delete(
        f"/api/v1/users/me/provider-documents/{doc['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 204

    listing = await client.get(
        "/api/v1/users/me/provider-documents",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.json()["data"] == []

    # Soft delete: row still in DB with is_deleted=true.
    rows = (await db_session.execute(
        select(Document).where(Document.id == uuid.UUID(doc["id"]))
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].is_deleted is True


@pytest.mark.asyncio
async def test_cross_user_delete_returns_404(
    client: AsyncClient, db_session: AsyncSession,
) -> None:
    alice = await _login(client, "doc-alice@test.com")
    bob = await _login(client, "doc-bob@test.com")
    await _activate(client, alice)
    await _activate(client, bob)
    alice_doc = await _upload_doc(client, alice)

    resp = await client.delete(
        f"/api/v1/users/me/provider-documents/{alice_doc['id']}",
        headers={"Authorization": f"Bearer {bob}"},
    )
    assert resp.status_code == 404
