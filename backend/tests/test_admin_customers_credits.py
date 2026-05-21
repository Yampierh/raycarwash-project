"""
tests/test_admin_customers_credits.py — Plan 24 W2-E.

Covers:
  - GET  /api/v1/admin/customers (segment + search + pagination)
  - POST /api/v1/admin/customers/{id}/credits

Scenarios:
  - Auth gate (anon/client/detailer → 401/403)
  - Empty list shape
  - Segment classification: new (0 appts) / active (recent) /
    dormant (old) / vip (≥10 appts OR ≥ $1,000 lifetime spend)
  - segment=all returns everyone; specific segment filters in-place
  - search by email
  - issue credit: validation (amount > 0, reason length), 404 unknown user,
    happy path persists and reflects in credit_balance_cents
  - audit log row written
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.appointments.models import Appointment, AppointmentStatus
from domains.audit.models import AuditAction, AuditLog
from domains.credits.models import CustomerCredit
from domains.services_catalog.models import Service
from tests.conftest import _create_user_with_role, get_access_token


CUSTOMERS_PATH = "/api/v1/admin/customers"
CREDITS_PATH = "/api/v1/admin/customers/{user_id}/credits"


# ── Helpers ────────────────────────────────────────────────────────── #


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict:
    await _create_user_with_role(db, "cust-admin@test.com", "Cust Admin", "admin")
    token = await get_access_token(client, "cust-admin@test.com")
    return {"Authorization": f"Bearer {token}"}


async def _any_service_id(db: AsyncSession) -> uuid.UUID:
    return (await db.execute(select(Service).limit(1))).scalar_one().id


async def _make_customer(
    db: AsyncSession,
    email: str,
    appointments: int = 0,
    last_appt_days_ago: int = 0,
    price_each: int = 10_000,
) -> uuid.UUID:
    """Create a client with N completed appointments."""
    user = await _create_user_with_role(db, email, "Cust " + email, "client")
    if appointments == 0:
        return user.id

    # We need a real detailer + service for the FK constraints
    detailer = await _create_user_with_role(
        db, f"det-{email}", "Det", "detailer",
    )
    service_id = await _any_service_id(db)
    base = datetime.now(timezone.utc) - timedelta(days=last_appt_days_ago)
    for i in range(appointments):
        db.add(Appointment(
            client_id=user.id,
            detailer_id=detailer.id,
            service_id=service_id,
            scheduled_time=base - timedelta(days=i),
            estimated_price=price_each,
            actual_price=price_each,
            status=AppointmentStatus.COMPLETED,
        ))
    await db.commit()
    return user.id


# ── Auth ───────────────────────────────────────────────────────────── #


class TestAuth:
    @pytest.mark.asyncio
    async def test_list_anon_401(self, client: AsyncClient):
        resp = await client.get(CUSTOMERS_PATH)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_client_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "lc-c@test.com", "C", "client")
        token = await get_access_token(client, "lc-c@test.com")
        resp = await client.get(
            CUSTOMERS_PATH, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_issue_anon_401(self, client: AsyncClient):
        resp = await client.post(
            CREDITS_PATH.format(user_id=uuid.uuid4()),
            json={"amount_cents": 500, "reason": "comp"},
        )
        assert resp.status_code == 401


# ── List + segments ────────────────────────────────────────────────── #


class TestList:
    @pytest.mark.asyncio
    async def test_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get(CUSTOMERS_PATH, headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["customers"] == []

    @pytest.mark.asyncio
    async def test_new_segment(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _make_customer(db_session, "new1@test.com", appointments=0)
        resp = await client.get(CUSTOMERS_PATH, headers=headers)
        assert resp.json()["customers"][0]["segment"] == "new"

    @pytest.mark.asyncio
    async def test_active_segment(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _make_customer(
            db_session, "act1@test.com", appointments=2, last_appt_days_ago=5,
        )
        resp = await client.get(CUSTOMERS_PATH, headers=headers)
        body = resp.json()
        target = next(c for c in body["customers"] if c["email"] == "act1@test.com")
        assert target["segment"] == "active"
        assert target["appointments_count"] == 2
        assert target["lifetime_spend_cents"] == 20_000

    @pytest.mark.asyncio
    async def test_dormant_segment(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        # 2 appts but the most recent was 120 days ago → dormant
        await _make_customer(
            db_session, "dor1@test.com", appointments=2, last_appt_days_ago=120,
        )
        resp = await client.get(CUSTOMERS_PATH, headers=headers)
        target = next(c for c in resp.json()["customers"] if c["email"] == "dor1@test.com")
        assert target["segment"] == "dormant"

    @pytest.mark.asyncio
    async def test_vip_by_count(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _make_customer(
            db_session, "vip1@test.com", appointments=10,
            last_appt_days_ago=5, price_each=5_000,
        )
        resp = await client.get(CUSTOMERS_PATH, headers=headers)
        target = next(c for c in resp.json()["customers"] if c["email"] == "vip1@test.com")
        assert target["segment"] == "vip"

    @pytest.mark.asyncio
    async def test_vip_by_spend(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        # 2 appts × $600 = $1,200 → vip by spend
        await _make_customer(
            db_session, "vip2@test.com", appointments=2,
            last_appt_days_ago=5, price_each=60_000,
        )
        resp = await client.get(CUSTOMERS_PATH, headers=headers)
        target = next(c for c in resp.json()["customers"] if c["email"] == "vip2@test.com")
        assert target["segment"] == "vip"

    @pytest.mark.asyncio
    async def test_segment_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _make_customer(db_session, "f-new@test.com", appointments=0)
        await _make_customer(
            db_session, "f-act@test.com", appointments=2, last_appt_days_ago=5,
        )
        resp = await client.get(
            CUSTOMERS_PATH, params={"segment": "active"}, headers=headers,
        )
        emails = [c["email"] for c in resp.json()["customers"]]
        assert "f-act@test.com" in emails
        assert "f-new@test.com" not in emails

    @pytest.mark.asyncio
    async def test_invalid_segment_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get(
            CUSTOMERS_PATH, params={"segment": "platinum"}, headers=headers,
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_search(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _make_customer(db_session, "search-target@test.com", appointments=0)
        await _make_customer(db_session, "other@test.com", appointments=0)
        resp = await client.get(
            CUSTOMERS_PATH, params={"search": "search-target"}, headers=headers,
        )
        body = resp.json()
        assert body["total"] == 1
        assert body["customers"][0]["email"] == "search-target@test.com"


# ── Issue credit ───────────────────────────────────────────────────── #


class TestIssueCredit:
    @pytest.mark.asyncio
    async def test_happy_path(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        user_id = await _make_customer(db_session, "cred1@test.com")
        resp = await client.post(
            CREDITS_PATH.format(user_id=user_id),
            json={"amount_cents": 2_500, "reason": "Apology for late detailer"},
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["amount_cents"] == 2_500
        assert body["status"] == "active"
        assert body["source"] == "admin_comp"
        assert body["user_id"] == str(user_id)

        # And balance shows up in /customers
        list_resp = await client.get(CUSTOMERS_PATH, headers=headers)
        target = next(
            c for c in list_resp.json()["customers"]
            if c["email"] == "cred1@test.com"
        )
        assert target["credit_balance_cents"] == 2_500

    @pytest.mark.asyncio
    async def test_amount_must_be_positive(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        user_id = await _make_customer(db_session, "cred2@test.com")
        resp = await client.post(
            CREDITS_PATH.format(user_id=user_id),
            json={"amount_cents": 0, "reason": "zero"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_amount_capped(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        user_id = await _make_customer(db_session, "cred3@test.com")
        # Over $10,000 cap
        resp = await client.post(
            CREDITS_PATH.format(user_id=user_id),
            json={"amount_cents": 10_001_00, "reason": "too much"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_reason_min_length(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        user_id = await _make_customer(db_session, "cred4@test.com")
        resp = await client.post(
            CREDITS_PATH.format(user_id=user_id),
            json={"amount_cents": 500, "reason": "x"},
            headers=headers,
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unknown_user_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            CREDITS_PATH.format(user_id=uuid.uuid4()),
            json={"amount_cents": 500, "reason": "ghost"},
            headers=headers,
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_audit_log_written(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        user_id = await _make_customer(db_session, "cred5@test.com")
        resp = await client.post(
            CREDITS_PATH.format(user_id=user_id),
            json={"amount_cents": 1_500, "reason": "Loyalty bonus"},
            headers=headers,
        )
        credit_id = resp.json()["id"]
        rows = (await db_session.execute(
            select(AuditLog).where(
                AuditLog.entity_type == "customer_credit",
                AuditLog.entity_id == credit_id,
                AuditLog.action == AuditAction.CUSTOMER_CREDIT_ISSUED,
            )
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].metadata_["reason"] == "Loyalty bonus"
        assert rows[0].new_value["amount_cents"] == 1_500

    @pytest.mark.asyncio
    async def test_db_row_persisted(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        user_id = await _make_customer(db_session, "cred6@test.com")
        await client.post(
            CREDITS_PATH.format(user_id=user_id),
            json={"amount_cents": 750, "reason": "Manual adjustment", "source": "adjustment"},
            headers=headers,
        )
        row = (await db_session.execute(
            select(CustomerCredit).where(CustomerCredit.user_id == user_id)
        )).scalar_one()
        assert row.amount_cents == 750
        assert row.source == "adjustment"
        assert row.status == "active"
