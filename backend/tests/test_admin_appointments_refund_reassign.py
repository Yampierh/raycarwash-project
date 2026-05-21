"""
tests/test_admin_appointments_refund_reassign.py — Plan 24 W2-B.

Covers:
  - POST /api/v1/admin/appointments/{id}/refund
  - POST /api/v1/admin/appointments/{id}/reassign

Refund relies on PaymentService.create_refund() which auto-detects the
stub Stripe key in the test env and returns a fake `re_stub_<hex>` id.

Scenarios:
  - Auth gate (anon/client/detailer → 401/403)
  - 404 on unknown appointment id
  - Refund: requires PaymentIntent; amount must be > 0; respects the
    appointment-price cap (no over-refund); writes Refund row + audit
    log; handles partial + cumulative refunds.
  - Reassign: requires existing approved detailer; can't be the same;
    can't be in non-reassignable status (IN_PROGRESS/COMPLETED); moves
    NO_DETAILER_FOUND → PENDING; writes audit log.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domains.appointments.models import Appointment, AppointmentStatus
from domains.audit.models import AuditAction, AuditLog
from domains.payments.models import Refund
from domains.providers.models import ProviderProfile
from domains.services_catalog.models import Service
from tests.conftest import _create_user_with_role, get_access_token


REFUND_PATH = "/api/v1/admin/appointments/{appointment_id}/refund"
REASSIGN_PATH = "/api/v1/admin/appointments/{appointment_id}/reassign"


# ── Helpers ────────────────────────────────────────────────────────── #


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict:
    await _create_user_with_role(db, "appt-admin@test.com", "Appt Admin", "admin")
    token = await get_access_token(client, "appt-admin@test.com")
    return {"Authorization": f"Bearer {token}"}


async def _any_service_id(db: AsyncSession) -> uuid.UUID:
    return (await db.execute(select(Service).limit(1))).scalar_one().id


async def _make_approved_detailer(
    db: AsyncSession, email: str,
) -> uuid.UUID:
    user = await _create_user_with_role(db, email, "Det " + email, "detailer")
    await db.execute(
        update(ProviderProfile)
        .where(ProviderProfile.user_id == user.id)
        .values(application_status="approved")
    )
    await db.commit()
    return user.id


async def _make_appointment(
    db: AsyncSession,
    *,
    client_email: str,
    detailer_id: uuid.UUID,
    status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    estimated_price: int = 20_000,
    actual_price: int | None = None,
    stripe_payment_intent_id: str | None = "pi_stub_for_test",
) -> uuid.UUID:
    customer = await _create_user_with_role(db, client_email, "Cust", "client")
    service_id = await _any_service_id(db)
    appt = Appointment(
        client_id=customer.id,
        detailer_id=detailer_id,
        service_id=service_id,
        scheduled_time=datetime(2026, 5, 19, 12, tzinfo=timezone.utc),
        estimated_price=estimated_price,
        actual_price=actual_price,
        status=status,
        stripe_payment_intent_id=stripe_payment_intent_id,
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return appt.id


# ── Auth ───────────────────────────────────────────────────────────── #


class TestRefundAuth:
    @pytest.mark.asyncio
    async def test_anon_401(self, client: AsyncClient):
        resp = await client.post(
            REFUND_PATH.format(appointment_id=uuid.uuid4()),
            json={"amount_cents": 100},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_client_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "rfc@test.com", "C", "client")
        token = await get_access_token(client, "rfc@test.com")
        resp = await client.post(
            REFUND_PATH.format(appointment_id=uuid.uuid4()),
            json={"amount_cents": 100},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestReassignAuth:
    @pytest.mark.asyncio
    async def test_anon_401(self, client: AsyncClient):
        resp = await client.post(
            REASSIGN_PATH.format(appointment_id=uuid.uuid4()),
            json={"new_detailer_id": str(uuid.uuid4()), "reason": "policy"},
        )
        assert resp.status_code == 401


# ── Refund ─────────────────────────────────────────────────────────── #


class TestRefund:
    @pytest.mark.asyncio
    async def test_unknown_appointment_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            REFUND_PATH.format(appointment_id=uuid.uuid4()),
            json={"amount_cents": 100},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_appointment_without_payment_intent_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        det_id = await _make_approved_detailer(db_session, "rfd1@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="rfc1@test.com", detailer_id=det_id,
            stripe_payment_intent_id=None,
        )
        resp = await client.post(
            REFUND_PATH.format(appointment_id=appt_id),
            json={"amount_cents": 500},
            headers=headers,
        )
        assert resp.status_code == 409
        assert "PaymentIntent" in resp.text

    @pytest.mark.asyncio
    async def test_amount_must_be_positive(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        det_id = await _make_approved_detailer(db_session, "rfd2@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="rfc2@test.com", detailer_id=det_id,
        )
        resp = await client.post(
            REFUND_PATH.format(appointment_id=appt_id),
            json={"amount_cents": 0},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_amount_exceeds_cap_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        det_id = await _make_approved_detailer(db_session, "rfd3@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="rfc3@test.com", detailer_id=det_id,
            estimated_price=20_000,
        )
        resp = await client.post(
            REFUND_PATH.format(appointment_id=appt_id),
            json={"amount_cents": 25_000},
            headers=headers,
        )
        assert resp.status_code == 409
        assert "cap" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_happy_path_persists_refund(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        det_id = await _make_approved_detailer(db_session, "rfd4@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="rfc4@test.com", detailer_id=det_id,
            estimated_price=20_000,
        )
        resp = await client.post(
            REFUND_PATH.format(appointment_id=appt_id),
            json={"amount_cents": 5_000, "reason": "requested_by_customer", "note": "weather"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["amount_cents"] == 5_000
        # Stub key path returns a re_stub_xxx id
        assert body["stripe_refund_id"].startswith("re_stub_")
        assert body["status"] == "succeeded"

        # DB row exists
        row = (await db_session.execute(
            select(Refund).where(Refund.appointment_id == appt_id)
        )).scalar_one()
        assert row.amount_cents == 5_000
        assert row.metadata_["reason_code"] == "requested_by_customer"

    @pytest.mark.asyncio
    async def test_partial_then_cumulative_cap(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        det_id = await _make_approved_detailer(db_session, "rfd5@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="rfc5@test.com", detailer_id=det_id,
            estimated_price=20_000,
        )
        r1 = await client.post(
            REFUND_PATH.format(appointment_id=appt_id),
            json={"amount_cents": 12_000}, headers=headers,
        )
        assert r1.status_code == 200
        # Now request more than remaining cap → 409
        r2 = await client.post(
            REFUND_PATH.format(appointment_id=appt_id),
            json={"amount_cents": 9_000}, headers=headers,
        )
        assert r2.status_code == 409
        # But up to the remaining 8000 works
        r3 = await client.post(
            REFUND_PATH.format(appointment_id=appt_id),
            json={"amount_cents": 8_000}, headers=headers,
        )
        assert r3.status_code == 200

    @pytest.mark.asyncio
    async def test_audit_log_written(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        det_id = await _make_approved_detailer(db_session, "rfd6@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="rfc6@test.com", detailer_id=det_id,
        )
        await client.post(
            REFUND_PATH.format(appointment_id=appt_id),
            json={"amount_cents": 1_000, "note": "service quality"},
            headers=headers,
        )
        rows = (await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "appointment",
                AuditLog.entity_id == str(appt_id),
                AuditLog.action == AuditAction.PAYMENT_REFUNDED,
            )
        )).scalars().all()
        assert len(rows) >= 1
        assert rows[-1].metadata_["action"] == "appointment_refund"


# ── Reassign ───────────────────────────────────────────────────────── #


class TestReassign:
    @pytest.mark.asyncio
    async def test_unknown_appointment_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        new_det = await _make_approved_detailer(db_session, "ra-det@test.com")
        resp = await client.post(
            REASSIGN_PATH.format(appointment_id=uuid.uuid4()),
            json={"new_detailer_id": str(new_det), "reason": "swap detailer"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_happy_path(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        old_det = await _make_approved_detailer(db_session, "ra-old@test.com")
        new_det = await _make_approved_detailer(db_session, "ra-new@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="ra-c@test.com", detailer_id=old_det,
            status=AppointmentStatus.CONFIRMED,
        )
        resp = await client.post(
            REASSIGN_PATH.format(appointment_id=appt_id),
            json={"new_detailer_id": str(new_det), "reason": "Original cancelled"},
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["previous_detailer_id"] == str(old_det)
        assert body["new_detailer_id"] == str(new_det)
        assert body["appointment_status"] == "confirmed"

        # DB reflects the change
        appt = (await db_session.execute(
            select(Appointment).where(Appointment.id == appt_id)
        )).scalar_one()
        await db_session.refresh(appt)
        assert appt.detailer_id == new_det

    @pytest.mark.asyncio
    async def test_no_detailer_found_promotes_to_pending(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        new_det = await _make_approved_detailer(db_session, "ra-rescue@test.com")
        # Appointment is orphaned — no detailer assigned
        customer = await _create_user_with_role(db_session, "ra-orph@test.com", "C", "client")
        service_id = await _any_service_id(db_session)
        appt = Appointment(
            client_id=customer.id,
            detailer_id=None,
            service_id=service_id,
            scheduled_time=datetime(2026, 5, 19, 12, tzinfo=timezone.utc),
            estimated_price=10_000,
            status=AppointmentStatus.NO_DETAILER_FOUND,
        )
        db_session.add(appt)
        await db_session.commit()
        await db_session.refresh(appt)

        resp = await client.post(
            REASSIGN_PATH.format(appointment_id=appt.id),
            json={"new_detailer_id": str(new_det), "reason": "Manual rescue"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["appointment_status"] == "pending"

    @pytest.mark.asyncio
    async def test_same_detailer_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        det = await _make_approved_detailer(db_session, "ra-same@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="ra-s@test.com", detailer_id=det,
        )
        resp = await client.post(
            REASSIGN_PATH.format(appointment_id=appt_id),
            json={"new_detailer_id": str(det), "reason": "no change"},
            headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_target_not_detailer_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        det = await _make_approved_detailer(db_session, "ra-from@test.com")
        # Target is a client, not a detailer
        client_user = await _create_user_with_role(db_session, "ra-target-c@test.com", "C", "client")
        appt_id = await _make_appointment(
            db_session, client_email="ra-c2@test.com", detailer_id=det,
        )
        resp = await client.post(
            REASSIGN_PATH.format(appointment_id=appt_id),
            json={"new_detailer_id": str(client_user.id), "reason": "swap detailer"},
            headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_target_unapproved_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        det_from = await _make_approved_detailer(db_session, "ra-from2@test.com")
        # Create detailer but leave as draft
        pending_det_user = await _create_user_with_role(
            db_session, "ra-pending@test.com", "D", "detailer",
        )
        appt_id = await _make_appointment(
            db_session, client_email="ra-c3@test.com", detailer_id=det_from,
        )
        resp = await client.post(
            REASSIGN_PATH.format(appointment_id=appt_id),
            json={"new_detailer_id": str(pending_det_user.id), "reason": "swap detailer"},
            headers=headers,
        )
        assert resp.status_code == 409
        assert "not approved" in resp.text.lower()

    @pytest.mark.asyncio
    async def test_completed_status_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        old_det = await _make_approved_detailer(db_session, "ra-cold@test.com")
        new_det = await _make_approved_detailer(db_session, "ra-cnew@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="ra-cc@test.com", detailer_id=old_det,
            status=AppointmentStatus.COMPLETED,
        )
        resp = await client.post(
            REASSIGN_PATH.format(appointment_id=appt_id),
            json={"new_detailer_id": str(new_det), "reason": "too late"},
            headers=headers,
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_audit_log_written(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        old_det = await _make_approved_detailer(db_session, "ra-aold@test.com")
        new_det = await _make_approved_detailer(db_session, "ra-anew@test.com")
        appt_id = await _make_appointment(
            db_session, client_email="ra-ac@test.com", detailer_id=old_det,
        )
        await client.post(
            REASSIGN_PATH.format(appointment_id=appt_id),
            json={"new_detailer_id": str(new_det), "reason": "Audit test"},
            headers=headers,
        )
        rows = (await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "appointment",
                AuditLog.entity_id == str(appt_id),
                AuditLog.action == AuditAction.APPOINTMENT_STATUS_CHANGED,
            )
        )).scalars().all()
        match = [r for r in rows if (r.metadata_ or {}).get("action") == "appointment_reassign"]
        assert len(match) == 1
        assert match[0].new_value == {"detailer_id": str(new_det)}
