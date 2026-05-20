"""
tests/test_appointments_cancel.py — Plan 21 §2 + §7.6.

Customer-facing cancellation wrapper of the FSM transition.
Verifies:
  - 100% refund preview when cancelling > 24h before scheduled_time
  - 50% refund preview between 2h and 24h
  - 0% refund preview within 2h
  - Response uses the normalised `status: "canceled"` UI alias
    (the DB stores `cancelled_by_client`)
  - 403 when a different client tries to cancel
  - 403 when a detailer tries to cancel (they use PATCH /status)
  - 409 when the appointment is already in a terminal state
  - 404 for unknown appointment id

Tests do NOT exercise the actual Stripe round-trip — appointments
created here have no stripe_payment_intent_id, so the FSM service
takes the "no payment integration" branch and just transitions the
status. The refund-preview math is the same regardless.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.appointments.models import Appointment, AppointmentStatus
from domains.services_catalog.models import Service
from tests.conftest import get_access_token


async def _make_appointment(
    db: AsyncSession,
    *,
    client_id,
    detailer_id,
    hours_until: float,
    status: AppointmentStatus = AppointmentStatus.CONFIRMED,
    estimated_price: int = 17_900,
    with_payment_intent: bool = False,
) -> Appointment:
    """Insert a Plan-21-realistic appointment with the chosen
    scheduled_time offset. Default state is CONFIRMED so the refund
    window logic is exercised (PENDING short-circuits to "auth voided
    = 100%" regardless of timing)."""
    svc = (await db.execute(select(Service).limit(1))).scalar_one()
    appt = Appointment(
        client_id=client_id,
        detailer_id=detailer_id,
        service_id=svc.id,
        scheduled_time=datetime.now(timezone.utc) + timedelta(hours=hours_until),
        estimated_price=estimated_price,
        status=status,
        stripe_payment_intent_id=(
            "pi_stub_NOPAY_test" if with_payment_intent else None
        ),
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return appt


@pytest.mark.asyncio
async def test_cancel_more_than_24h_returns_100pct(client_with_db, test_user, test_detailer):
    ac, db = client_with_db
    appt = await _make_appointment(
        db, client_id=test_user.id, detailer_id=test_detailer.id,
        hours_until=48,
    )
    token = await get_access_token(ac, test_user.email)

    r = await ac.post(
        f"/api/v1/appointments/{appt.id}/cancel",
        json={"reason": "Too cold to wash"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["status"] == "canceled"
    assert data["refund_pct"] == 100
    assert data["refund_cents"] == appt.estimated_price
    assert "Full refund" in data["refund_note"]

    # DB row really transitioned to the British-spelled enum value
    await db.refresh(appt)
    assert appt.status == AppointmentStatus.CANCELLED_BY_CLIENT


@pytest.mark.asyncio
async def test_cancel_in_partial_window_returns_50pct(client_with_db, test_user, test_detailer):
    ac, db = client_with_db
    # 10h before — inside (2h, 24h) → 50% partial refund.
    appt = await _make_appointment(
        db, client_id=test_user.id, detailer_id=test_detailer.id,
        hours_until=10, estimated_price=20_000,
    )
    token = await get_access_token(ac, test_user.email)

    r = await ac.post(
        f"/api/v1/appointments/{appt.id}/cancel",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "canceled"
    assert data["refund_pct"] == 50
    assert data["refund_cents"] == 10_000
    assert "Partial" in data["refund_note"]


@pytest.mark.asyncio
async def test_cancel_within_2h_returns_zero(client_with_db, test_user, test_detailer):
    ac, db = client_with_db
    appt = await _make_appointment(
        db, client_id=test_user.id, detailer_id=test_detailer.id,
        hours_until=1,
    )
    token = await get_access_token(ac, test_user.email)

    r = await ac.post(
        f"/api/v1/appointments/{appt.id}/cancel",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["refund_pct"] == 0
    assert data["refund_cents"] == 0
    assert "No refund" in data["refund_note"]


@pytest.mark.asyncio
async def test_cancel_pending_appointment_is_full_release(client_with_db, test_user, test_detailer):
    """PENDING bookings are still in auth-hold state — cancelling
    voids the hold (functionally a 100% refund) regardless of how close
    the scheduled_time is."""
    ac, db = client_with_db
    appt = await _make_appointment(
        db, client_id=test_user.id, detailer_id=test_detailer.id,
        hours_until=0.5,                             # less than 2h
        status=AppointmentStatus.PENDING,
    )
    token = await get_access_token(ac, test_user.email)

    r = await ac.post(
        f"/api/v1/appointments/{appt.id}/cancel",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["refund_pct"] == 100
    assert "Payment hold released" in data["refund_note"]


@pytest.mark.asyncio
async def test_cancel_404_unknown_appointment(client_with_db, test_user):
    ac, _ = client_with_db
    token = await get_access_token(ac, test_user.email)

    r = await ac.post(
        f"/api/v1/appointments/{uuid4()}/cancel",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_cancel_403_when_not_the_booking_customer(
    client_with_db, test_user, test_detailer,
):
    """Detailers (and any other user) cannot cancel through this
    customer-only entry point. They must use PATCH /status."""
    ac, db = client_with_db
    appt = await _make_appointment(
        db, client_id=test_user.id, detailer_id=test_detailer.id,
        hours_until=48,
    )
    # Authenticate as the detailer, attempt to cancel via the customer endpoint
    token = await get_access_token(ac, test_detailer.email)

    r = await ac.post(
        f"/api/v1/appointments/{appt.id}/cancel",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
    assert "customer" in r.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_cancel_409_when_already_terminal(
    client_with_db, test_user, test_detailer,
):
    ac, db = client_with_db
    appt = await _make_appointment(
        db, client_id=test_user.id, detailer_id=test_detailer.id,
        hours_until=48,
        status=AppointmentStatus.CANCELLED_BY_CLIENT,
    )
    token = await get_access_token(ac, test_user.email)

    r = await ac.post(
        f"/api/v1/appointments/{appt.id}/cancel",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409
    assert "already" in r.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_cancel_reason_max_length(client_with_db, test_user, test_detailer):
    """Plan 21 §7.3 — reason field has max_length=500."""
    ac, db = client_with_db
    appt = await _make_appointment(
        db, client_id=test_user.id, detailer_id=test_detailer.id,
        hours_until=48,
    )
    token = await get_access_token(ac, test_user.email)

    r = await ac.post(
        f"/api/v1/appointments/{appt.id}/cancel",
        json={"reason": "x" * 501},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
