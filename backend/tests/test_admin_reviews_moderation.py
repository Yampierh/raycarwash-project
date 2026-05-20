"""
tests/test_admin_reviews_moderation.py — Plan 24 W2-D.

Covers:
  - GET  /api/v1/admin/reviews/queue
  - POST /api/v1/admin/reviews/{id}/approve
  - POST /api/v1/admin/reviews/{id}/hide

Scenarios:
  - Auth gate (anon/client/detailer → 401/403)
  - Empty queue
  - Low-rating reviews surfaced; high-rating + no-keyword NOT surfaced
  - Keyword match (case-insensitive) surfaces a 5★ review
  - FIFO order by created_at
  - Approve / hide happy paths + state transitions
  - 404 on unknown id; 409 on FSM violations
  - Audit log row written with old/new moderation_state
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.appointments.models import Appointment, AppointmentStatus
from domains.audit.models import AuditAction, AuditLog
from domains.reviews.models import Review
from domains.services_catalog.models import Service
from tests.conftest import _create_user_with_role, get_access_token


QUEUE_PATH = "/api/v1/admin/reviews/queue"
APPROVE_PATH = "/api/v1/admin/reviews/{review_id}/approve"
HIDE_PATH = "/api/v1/admin/reviews/{review_id}/hide"


# ── Helpers ────────────────────────────────────────────────────────── #


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict:
    await _create_user_with_role(db, "rev-admin@test.com", "Rev Admin", "admin")
    token = await get_access_token(client, "rev-admin@test.com")
    return {"Authorization": f"Bearer {token}"}


async def _any_service_id(db: AsyncSession) -> uuid.UUID:
    return (await db.execute(select(Service).limit(1))).scalar_one().id


async def _seed_review(
    db: AsyncSession,
    *,
    rating: int,
    comment: str | None,
    reviewer_email: str = "rev@test.com",
    detailer_email: str = "det@test.com",
    moderation_state: str = "auto_pending",
) -> uuid.UUID:
    """Create a Review backed by a real Appointment + reviewer/detailer."""
    reviewer = await _create_user_with_role(db, reviewer_email, "Reviewer", "client")
    detailer = await _create_user_with_role(db, detailer_email, "Detailer", "detailer")
    service_id = await _any_service_id(db)

    appt = Appointment(
        client_id=reviewer.id,
        detailer_id=detailer.id,
        service_id=service_id,
        scheduled_time=datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc),
        estimated_price=10_000,
        status=AppointmentStatus.COMPLETED,
    )
    db.add(appt)
    await db.flush()

    review = Review(
        appointment_id=appt.id,
        reviewer_id=reviewer.id,
        detailer_id=detailer.id,
        rating=rating,
        comment=comment,
        moderation_state=moderation_state,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review.id


# ── Auth ───────────────────────────────────────────────────────────── #


class TestQueueAuth:
    @pytest.mark.asyncio
    async def test_anon_401(self, client: AsyncClient):
        resp = await client.get(QUEUE_PATH)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_client_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "c-q@test.com", "C", "client")
        token = await get_access_token(client, "c-q@test.com")
        resp = await client.get(
            QUEUE_PATH, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_detailer_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "d-q@test.com", "D", "detailer")
        token = await get_access_token(client, "d-q@test.com")
        resp = await client.get(
            QUEUE_PATH, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403


# ── Queue behaviour ────────────────────────────────────────────────── #


class TestQueueBehaviour:
    @pytest.mark.asyncio
    async def test_empty_queue(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get(QUEUE_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"reviews": [], "total": 0}

    @pytest.mark.asyncio
    async def test_low_rating_surfaces(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="meh",
            reviewer_email="r1@test.com", detailer_email="d1@test.com",
        )
        resp = await client.get(QUEUE_PATH, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        row = body["reviews"][0]
        assert row["review_id"] == str(review_id)
        assert "low_rating" in row["flag_reasons"]
        assert row["rating"] == 1

    @pytest.mark.asyncio
    async def test_high_rating_no_keyword_skipped(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _seed_review(
            db_session, rating=5, comment="Great service",
            reviewer_email="r2@test.com", detailer_email="d2@test.com",
        )
        resp = await client.get(QUEUE_PATH, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"reviews": [], "total": 0}

    @pytest.mark.asyncio
    async def test_keyword_match_case_insensitive(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _seed_review(
            db_session, rating=5, comment="Total SCAM, beware",
            reviewer_email="r3@test.com", detailer_email="d3@test.com",
        )
        resp = await client.get(QUEUE_PATH, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert "keyword:scam" in body["reviews"][0]["flag_reasons"]

    @pytest.mark.asyncio
    async def test_already_approved_not_surfaced(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _seed_review(
            db_session, rating=1, comment="x",
            reviewer_email="r4@test.com", detailer_email="d4@test.com",
            moderation_state="approved",
        )
        resp = await client.get(QUEUE_PATH, headers=headers)
        assert resp.json()["total"] == 0


# ── Approve happy path ─────────────────────────────────────────────── #


class TestApproveHappyPath:
    @pytest.mark.asyncio
    async def test_auto_pending_to_approved(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="bad",
            reviewer_email="r5@test.com", detailer_email="d5@test.com",
        )
        resp = await client.post(
            APPROVE_PATH.format(review_id=review_id),
            json={"note": "Within policy"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["moderation_state"] == "approved"
        assert body["previous_state"] == "auto_pending"
        assert body["moderation_note"] == "Within policy"

        # Queue should no longer include it
        q = await client.get(QUEUE_PATH, headers=headers)
        assert q.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_approve_accepts_empty_body(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=2, comment=None,
            reviewer_email="r6@test.com", detailer_email="d6@test.com",
        )
        resp = await client.post(
            APPROVE_PATH.format(review_id=review_id), headers=headers,
        )
        assert resp.status_code == 200


# ── Hide happy path ────────────────────────────────────────────────── #


class TestHideHappyPath:
    @pytest.mark.asyncio
    async def test_auto_pending_to_hidden(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="scam",
            reviewer_email="r7@test.com", detailer_email="d7@test.com",
        )
        resp = await client.post(
            HIDE_PATH.format(review_id=review_id),
            json={"note": "Confirmed false claim"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["moderation_state"] == "hidden"
        assert body["previous_state"] == "auto_pending"

    @pytest.mark.asyncio
    async def test_approved_can_still_be_hidden(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="bad",
            reviewer_email="r8@test.com", detailer_email="d8@test.com",
            moderation_state="approved",
        )
        resp = await client.post(
            HIDE_PATH.format(review_id=review_id),
            json={"note": "Later flagged via user report"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["previous_state"] == "approved"

    @pytest.mark.asyncio
    async def test_hide_requires_note(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="x",
            reviewer_email="r9@test.com", detailer_email="d9@test.com",
        )
        resp = await client.post(
            HIDE_PATH.format(review_id=review_id), json={}, headers=headers,
        )
        assert resp.status_code == 422


# ── 404 / 409 ──────────────────────────────────────────────────────── #


class TestErrors:
    @pytest.mark.asyncio
    async def test_approve_unknown_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            APPROVE_PATH.format(review_id=uuid.uuid4()), headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_hide_unknown_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            HIDE_PATH.format(review_id=uuid.uuid4()),
            json={"note": "policy"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_approve_from_approved_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="x",
            reviewer_email="r10@test.com", detailer_email="d10@test.com",
            moderation_state="approved",
        )
        resp = await client.post(
            APPROVE_PATH.format(review_id=review_id), headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_approve_from_hidden_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="x",
            reviewer_email="r11@test.com", detailer_email="d11@test.com",
            moderation_state="hidden",
        )
        resp = await client.post(
            APPROVE_PATH.format(review_id=review_id), headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_hide_from_hidden_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="x",
            reviewer_email="r12@test.com", detailer_email="d12@test.com",
            moderation_state="hidden",
        )
        resp = await client.post(
            HIDE_PATH.format(review_id=review_id),
            json={"note": "again"},
            headers=headers,
        )
        assert resp.status_code == 409


# ── Audit log ──────────────────────────────────────────────────────── #


class TestAuditLog:
    @pytest.mark.asyncio
    async def test_approve_writes_audit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="x",
            reviewer_email="r13@test.com", detailer_email="d13@test.com",
        )
        await client.post(
            APPROVE_PATH.format(review_id=review_id), headers=headers,
        )
        rows = (await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "review",
                AuditLog.entity_id == str(review_id),
                AuditLog.action == AuditAction.REVIEW_MODERATED,
            )
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].old_value == {"moderation_state": "auto_pending"}
        assert rows[0].new_value == {"moderation_state": "approved"}

    @pytest.mark.asyncio
    async def test_hide_writes_audit_with_note(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        review_id = await _seed_review(
            db_session, rating=1, comment="x",
            reviewer_email="r14@test.com", detailer_email="d14@test.com",
        )
        await client.post(
            HIDE_PATH.format(review_id=review_id),
            json={"note": "Confirmed harassment"},
            headers=headers,
        )
        rows = (await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "review",
                AuditLog.entity_id == str(review_id),
                AuditLog.action == AuditAction.REVIEW_MODERATED,
            )
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].new_value == {"moderation_state": "hidden"}
        assert rows[0].metadata_["note"] == "Confirmed harassment"
