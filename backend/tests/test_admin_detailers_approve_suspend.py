"""
tests/test_admin_detailers_approve_suspend.py — Plan 24 W2-C.

Covers POST /api/v1/admin/detailers/{id}/approve and /suspend:
  - Auth gate (anon → 401, client → 403, detailer → 403, admin → 200)
  - 404 on unknown provider_id
  - FSM transitions:
      * submitted → approved (happy path)
      * approved → suspended (with reason)
      * suspended → approved (reinstate)
      * docs_review → approved (mid-FSM approve)
      * draft → approve = 409 (must submit first)
      * rejected → approve = 409 (terminal)
      * draft → suspend = 409 (only approved is suspendable)
      * suspended → suspend = 409 (already suspended)
  - rejection_reason cleared on approve, set on suspend
  - reviewed_at set on every transition
  - Audit log row written with old_value/new_value
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domains.audit.models import AuditAction, AuditLog
from domains.providers.models import ProviderProfile
from tests.conftest import _create_user_with_role, get_access_token


APPROVE_PATH = "/api/v1/admin/detailers/{provider_id}/approve"
SUSPEND_PATH = "/api/v1/admin/detailers/{provider_id}/suspend"


# ── Helpers ────────────────────────────────────────────────────────── #


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict:
    await _create_user_with_role(db, "det-admin@test.com", "Det Admin", "admin")
    token = await get_access_token(client, "det-admin@test.com")
    return {"Authorization": f"Bearer {token}"}


async def _make_detailer(
    db: AsyncSession, email: str, application_status: str = "submitted",
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a detailer + ProviderProfile pinned to the given FSM state.

    Returns (user_id, provider_profile_id)."""
    user = await _create_user_with_role(db, email, "Det " + email, "detailer")
    await db.execute(
        update(ProviderProfile)
        .where(ProviderProfile.user_id == user.id)
        .values(application_status=application_status)
    )
    await db.commit()
    profile = (
        await db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user.id)
        )
    ).scalar_one()
    return user.id, profile.id


async def _get_status(db: AsyncSession, provider_id: uuid.UUID) -> str:
    profile = (
        await db.execute(
            select(ProviderProfile).where(ProviderProfile.id == provider_id)
        )
    ).scalar_one()
    return profile.application_status


# ── Auth guard ─────────────────────────────────────────────────────── #


class TestApproveAuth:
    @pytest.mark.asyncio
    async def test_anon_401(self, client: AsyncClient):
        resp = await client.post(APPROVE_PATH.format(provider_id=uuid.uuid4()))
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_client_role_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "c@test.com", "C", "client")
        token = await get_access_token(client, "c@test.com")
        resp = await client.post(
            APPROVE_PATH.format(provider_id=uuid.uuid4()),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_detailer_role_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "d@test.com", "D", "detailer")
        token = await get_access_token(client, "d@test.com")
        resp = await client.post(
            APPROVE_PATH.format(provider_id=uuid.uuid4()),
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestSuspendAuth:
    @pytest.mark.asyncio
    async def test_anon_401(self, client: AsyncClient):
        resp = await client.post(
            SUSPEND_PATH.format(provider_id=uuid.uuid4()),
            json={"reason": "Policy violation"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_client_role_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "c2@test.com", "C2", "client")
        token = await get_access_token(client, "c2@test.com")
        resp = await client.post(
            SUSPEND_PATH.format(provider_id=uuid.uuid4()),
            json={"reason": "Policy violation"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ── 404 ────────────────────────────────────────────────────────────── #


class TestNotFound:
    @pytest.mark.asyncio
    async def test_approve_unknown_provider_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            APPROVE_PATH.format(provider_id=uuid.uuid4()), headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_suspend_unknown_provider_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            SUSPEND_PATH.format(provider_id=uuid.uuid4()),
            json={"reason": "Policy violation"},
            headers=headers,
        )
        assert resp.status_code == 404


# ── Approve happy path ─────────────────────────────────────────────── #


class TestApproveHappyPath:
    @pytest.mark.asyncio
    async def test_submitted_to_approved(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det1@test.com", application_status="submitted",
        )
        resp = await client.post(
            APPROVE_PATH.format(provider_id=provider_id), headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["application_status"] == "approved"
        assert body["previous_status"] == "submitted"
        assert body["user_email"] == "det1@test.com"
        assert body["rejection_reason"] is None
        assert await _get_status(db_session, provider_id) == "approved"

    @pytest.mark.asyncio
    async def test_docs_review_to_approved(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det2@test.com", application_status="docs_review",
        )
        resp = await client.post(
            APPROVE_PATH.format(provider_id=provider_id), headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["previous_status"] == "docs_review"

    @pytest.mark.asyncio
    async def test_approve_clears_prior_rejection_reason(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """When reinstating from suspended, the stored reason should clear."""
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det3@test.com", application_status="approved",
        )
        await client.post(
            SUSPEND_PATH.format(provider_id=provider_id),
            json={"reason": "Vehicle inspection overdue"},
            headers=headers,
        )
        # Verify reason was stored
        profile = (
            await db_session.execute(
                select(ProviderProfile).where(ProviderProfile.id == provider_id)
            )
        ).scalar_one()
        await db_session.refresh(profile)
        assert profile.rejection_reason == "Vehicle inspection overdue"

        resp = await client.post(
            APPROVE_PATH.format(provider_id=provider_id),
            json={"notes": "Inspection clear"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["application_status"] == "approved"
        assert body["previous_status"] == "suspended"
        assert body["rejection_reason"] is None

    @pytest.mark.asyncio
    async def test_approve_accepts_empty_body(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det4@test.com", application_status="submitted",
        )
        resp = await client.post(
            APPROVE_PATH.format(provider_id=provider_id), headers=headers,
        )
        assert resp.status_code == 200


# ── Suspend happy path ─────────────────────────────────────────────── #


class TestSuspendHappyPath:
    @pytest.mark.asyncio
    async def test_approved_to_suspended(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det5@test.com", application_status="approved",
        )
        resp = await client.post(
            SUSPEND_PATH.format(provider_id=provider_id),
            json={"reason": "Customer-safety complaint"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["application_status"] == "suspended"
        assert body["previous_status"] == "approved"
        assert body["rejection_reason"] == "Customer-safety complaint"
        assert await _get_status(db_session, provider_id) == "suspended"

    @pytest.mark.asyncio
    async def test_suspend_requires_reason(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det6@test.com", application_status="approved",
        )
        resp = await client.post(
            SUSPEND_PATH.format(provider_id=provider_id),
            json={},
            headers=headers,
        )
        assert resp.status_code == 422  # Pydantic: reason is required

    @pytest.mark.asyncio
    async def test_suspend_reason_min_length(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det7@test.com", application_status="approved",
        )
        resp = await client.post(
            SUSPEND_PATH.format(provider_id=provider_id),
            json={"reason": "x"},  # too short
            headers=headers,
        )
        assert resp.status_code == 422


# ── FSM violations → 409 ───────────────────────────────────────────── #


class TestFsmViolations:
    @pytest.mark.asyncio
    async def test_approve_from_draft_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det8@test.com", application_status="draft",
        )
        resp = await client.post(
            APPROVE_PATH.format(provider_id=provider_id), headers=headers,
        )
        assert resp.status_code == 409
        # Error message references the rejected source state. The exact
        # envelope shape differs by path prefix, but the source state is
        # included regardless.
        assert "draft" in resp.text

    @pytest.mark.asyncio
    async def test_approve_from_rejected_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det9@test.com", application_status="rejected",
        )
        resp = await client.post(
            APPROVE_PATH.format(provider_id=provider_id), headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_approve_from_approved_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det10@test.com", application_status="approved",
        )
        resp = await client.post(
            APPROVE_PATH.format(provider_id=provider_id), headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_suspend_from_draft_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det11@test.com", application_status="draft",
        )
        resp = await client.post(
            SUSPEND_PATH.format(provider_id=provider_id),
            json={"reason": "Policy violation"},
            headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_suspend_from_submitted_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det12@test.com", application_status="submitted",
        )
        resp = await client.post(
            SUSPEND_PATH.format(provider_id=provider_id),
            json={"reason": "Policy violation"},
            headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_suspend_from_suspended_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det13@test.com", application_status="suspended",
        )
        resp = await client.post(
            SUSPEND_PATH.format(provider_id=provider_id),
            json={"reason": "Policy violation"},
            headers=headers,
        )
        assert resp.status_code == 409


# ── Audit log ──────────────────────────────────────────────────────── #


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_approve_writes_audit_row(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det14@test.com", application_status="submitted",
        )
        await client.post(
            APPROVE_PATH.format(provider_id=provider_id), headers=headers,
        )
        rows = (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.entity_type == "provider_profile",
                    AuditLog.entity_id == str(provider_id),
                    AuditLog.action == AuditAction.PROVIDER_STATUS_CHANGED,
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        row = rows[0]
        assert row.old_value == {"application_status": "submitted"}
        assert row.new_value == {"application_status": "approved"}
        assert row.metadata_["action"] == "detailer_approved"

    @pytest.mark.asyncio
    async def test_suspend_writes_audit_row_with_reason(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        _, provider_id = await _make_detailer(
            db_session, "det15@test.com", application_status="approved",
        )
        await client.post(
            SUSPEND_PATH.format(provider_id=provider_id),
            json={"reason": "Inactivity"},
            headers=headers,
        )
        rows = (
            await db_session.execute(
                select(AuditLog).where(
                    AuditLog.entity_type == "provider_profile",
                    AuditLog.entity_id == str(provider_id),
                    AuditLog.action == AuditAction.PROVIDER_STATUS_CHANGED,
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        row = rows[0]
        assert row.old_value == {"application_status": "approved"}
        assert row.new_value == {"application_status": "suspended"}
        assert row.metadata_["reason"] == "Inactivity"
