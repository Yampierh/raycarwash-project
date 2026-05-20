"""
tests/test_admin_ops_dashboard.py — Plan 24 W2-A.

Covers GET /api/v1/admin/ops/dashboard:
  - Auth guard (anon → 401, client → 403, detailer → 403, admin → 200)
  - Empty-state shape (all KPIs zero, heatmap empty, cities list seeded)
  - Window param validation (each enum value + invalid)
  - KPIs reflect created appointments (GMV, bookings count, active jobs)
  - City rollup populates per-city detailer/job counts
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed_cities import seed_cities
from domains.appointments.models import Appointment, AppointmentStatus
from domains.providers.models import ProviderProfile
from domains.services_catalog.models import Service
from tests.conftest import _create_user_with_role, get_access_token


PATH = "/api/v1/admin/ops/dashboard"


# ── Helpers ────────────────────────────────────────────────────────── #


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict:
    await _create_user_with_role(db, "ops-admin@test.com", "Ops Admin", "admin")
    token = await get_access_token(client, "ops-admin@test.com")
    return {"Authorization": f"Bearer {token}"}


async def _any_service_id(db: AsyncSession) -> uuid.UUID:
    """Return a Service id — conftest seeds services on every test."""
    from sqlalchemy import select

    return (await db.execute(select(Service).limit(1))).scalar_one().id


async def _make_detailer_in_city(
    db: AsyncSession, email: str, city_code: str
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a detailer with a ProviderProfile pinned to a city code.

    Returns (user_id, provider_profile_id).
    """
    user = await _create_user_with_role(db, email, "Det " + email, "detailer")
    from sqlalchemy import select, update

    await db.execute(
        update(ProviderProfile)
        .where(ProviderProfile.user_id == user.id)
        .values(home_city_code=city_code, application_status="approved")
    )
    await db.commit()
    profile = (
        await db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user.id)
        )
    ).scalar_one()
    return user.id, profile.id


async def _create_appointment(
    db: AsyncSession,
    *,
    client_id: uuid.UUID,
    detailer_id: uuid.UUID,
    service_id: uuid.UUID,
    status: AppointmentStatus,
    scheduled_time: datetime,
    estimated_price: int = 15_000,
    actual_price: int | None = None,
) -> uuid.UUID:
    appt = Appointment(
        client_id=client_id,
        detailer_id=detailer_id,
        service_id=service_id,
        scheduled_time=scheduled_time,
        status=status,
        estimated_price=estimated_price,
        actual_price=actual_price,
    )
    db.add(appt)
    await db.commit()
    await db.refresh(appt)
    return appt.id


# ── Auth guard ─────────────────────────────────────────────────────── #


class TestOpsDashboardAuth:
    @pytest.mark.asyncio
    async def test_anon_401(self, client: AsyncClient):
        resp = await client.get(PATH)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_client_role_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "c@test.com", "C", "client")
        token = await get_access_token(client, "c@test.com")
        resp = await client.get(
            PATH, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_detailer_role_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "d@test.com", "D", "detailer")
        token = await get_access_token(client, "d@test.com")
        resp = await client.get(
            PATH, headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403


# ── Shape + empty state ────────────────────────────────────────────── #


class TestOpsDashboardEmptyState:
    @pytest.mark.asyncio
    async def test_empty_db_returns_zero_kpis(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get(PATH, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Envelope shape — top-level fields.
        for key in ("window", "period_start", "period_end", "city", "kpis", "heatmap", "cities"):
            assert key in data, f"missing key: {key}"

        assert data["window"] == "7d"
        assert data["city"] == "all"

        # KPIs zeroed.
        k = data["kpis"]
        for tile in ("gmv_cents", "bookings", "active_jobs", "take_rate", "csat", "cancel_rate"):
            assert tile in k
            assert k[tile]["value"] == 0
            assert k[tile]["delta"] == 0
            assert k[tile]["spark"] == []

    @pytest.mark.asyncio
    async def test_seeded_cities_appear_in_rollup(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await seed_cities(db_session)
        headers = await _admin_headers(client, db_session)
        resp = await client.get(PATH, headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        codes = {c["code"] for c in data["cities"]}
        assert {"fwa", "ind", "col", "cin", "lou"}.issubset(codes)

        fwa = next(c for c in data["cities"] if c["code"] == "fwa")
        assert fwa["active"] is True
        assert fwa["status"] == "active"
        assert fwa["detailers"] == 0
        assert fwa["jobs"] == 0


# ── Window param ───────────────────────────────────────────────────── #


class TestOpsDashboardWindow:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("window", ["1h", "today", "7d", "30d", "90d"])
    async def test_each_window_accepted(
        self, client: AsyncClient, db_session: AsyncSession, window: str
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get(
            PATH, headers=headers, params={"window": window}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["window"] == window

    @pytest.mark.asyncio
    async def test_invalid_window_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get(
            PATH, headers=headers, params={"window": "yearly"}
        )
        # FastAPI/pydantic returns 422 on Literal mismatch.
        assert resp.status_code == 422


# ── KPIs reflect data ──────────────────────────────────────────────── #


class TestOpsDashboardKpisWithData:
    @pytest.mark.asyncio
    async def test_completed_appointment_contributes_to_gmv(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await seed_cities(db_session)
        cust = await _create_user_with_role(
            db_session, "kpi-cust@test.com", "Cust", "client"
        )
        det_id, _ = await _make_detailer_in_city(
            db_session, "kpi-det@test.com", "fwa"
        )
        svc_id = await _any_service_id(db_session)

        now = datetime.now(timezone.utc)
        # COMPLETED within the 7d window with actual_price set.
        await _create_appointment(
            db_session,
            client_id=cust.id,
            detailer_id=det_id,
            service_id=svc_id,
            status=AppointmentStatus.COMPLETED,
            scheduled_time=now - timedelta(days=1),
            estimated_price=15_000,
            actual_price=18_000,
        )

        headers = await _admin_headers(client, db_session)
        resp = await client.get(PATH, headers=headers, params={"window": "7d"})
        assert resp.status_code == 200, resp.text
        k = resp.json()["kpis"]
        assert k["gmv_cents"]["value"] == 18_000
        assert k["bookings"]["value"] == 1

    @pytest.mark.asyncio
    async def test_active_jobs_counts_in_flight_appointments(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await seed_cities(db_session)
        cust = await _create_user_with_role(
            db_session, "active-cust@test.com", "Cust", "client"
        )
        det_id, _ = await _make_detailer_in_city(
            db_session, "active-det@test.com", "fwa"
        )
        svc_id = await _any_service_id(db_session)

        now = datetime.now(timezone.utc)
        for st in (
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.ARRIVED,
            AppointmentStatus.IN_PROGRESS,
            AppointmentStatus.COMPLETED,    # not counted as active
            AppointmentStatus.CANCELLED_BY_CLIENT,  # not counted
        ):
            await _create_appointment(
                db_session,
                client_id=cust.id,
                detailer_id=det_id,
                service_id=svc_id,
                status=st,
                scheduled_time=now - timedelta(hours=2),
            )

        headers = await _admin_headers(client, db_session)
        resp = await client.get(PATH, headers=headers, params={"window": "7d"})
        assert resp.status_code == 200, resp.text
        k = resp.json()["kpis"]
        assert k["active_jobs"]["value"] == 3   # CONFIRMED + ARRIVED + IN_PROGRESS
        assert k["bookings"]["value"] == 5      # all 5 fall in window

    @pytest.mark.asyncio
    async def test_cancel_rate_computed(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await seed_cities(db_session)
        cust = await _create_user_with_role(
            db_session, "cancel-cust@test.com", "Cust", "client"
        )
        det_id, _ = await _make_detailer_in_city(
            db_session, "cancel-det@test.com", "fwa"
        )
        svc_id = await _any_service_id(db_session)

        now = datetime.now(timezone.utc)
        # 1 completed + 1 cancelled → 50% cancel rate.
        await _create_appointment(
            db_session,
            client_id=cust.id,
            detailer_id=det_id,
            service_id=svc_id,
            status=AppointmentStatus.COMPLETED,
            scheduled_time=now - timedelta(days=1),
            actual_price=10_000,
        )
        await _create_appointment(
            db_session,
            client_id=cust.id,
            detailer_id=det_id,
            service_id=svc_id,
            status=AppointmentStatus.CANCELLED_BY_CLIENT,
            scheduled_time=now - timedelta(days=1),
        )

        headers = await _admin_headers(client, db_session)
        resp = await client.get(PATH, headers=headers, params={"window": "7d"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["kpis"]["cancel_rate"]["value"] == 50.0


# ── City rollup ────────────────────────────────────────────────────── #


class TestOpsDashboardCityRollup:
    @pytest.mark.asyncio
    async def test_detailer_count_bucketed_by_home_city(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await seed_cities(db_session)
        await _make_detailer_in_city(db_session, "fwa1@test.com", "fwa")
        await _make_detailer_in_city(db_session, "fwa2@test.com", "fwa")
        await _make_detailer_in_city(db_session, "ind1@test.com", "ind")

        headers = await _admin_headers(client, db_session)
        resp = await client.get(PATH, headers=headers)
        assert resp.status_code == 200, resp.text
        cities = {c["code"]: c for c in resp.json()["cities"]}
        assert cities["fwa"]["detailers"] == 2
        assert cities["ind"]["detailers"] == 1
        assert cities["col"]["detailers"] == 0

    @pytest.mark.asyncio
    async def test_city_filter_scopes_kpis(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await seed_cities(db_session)
        cust = await _create_user_with_role(
            db_session, "scope-cust@test.com", "Cust", "client"
        )
        fwa_det, _ = await _make_detailer_in_city(
            db_session, "scope-fwa@test.com", "fwa"
        )
        ind_det, _ = await _make_detailer_in_city(
            db_session, "scope-ind@test.com", "ind"
        )
        svc_id = await _any_service_id(db_session)

        now = datetime.now(timezone.utc)
        # One completed appt in each city.
        await _create_appointment(
            db_session,
            client_id=cust.id,
            detailer_id=fwa_det,
            service_id=svc_id,
            status=AppointmentStatus.COMPLETED,
            scheduled_time=now - timedelta(days=1),
            actual_price=12_000,
        )
        await _create_appointment(
            db_session,
            client_id=cust.id,
            detailer_id=ind_det,
            service_id=svc_id,
            status=AppointmentStatus.COMPLETED,
            scheduled_time=now - timedelta(days=1),
            actual_price=8_000,
        )

        headers = await _admin_headers(client, db_session)
        # All cities — GMV should be 20_000.
        all_resp = await client.get(PATH, headers=headers, params={"city": "all"})
        assert all_resp.status_code == 200
        assert all_resp.json()["kpis"]["gmv_cents"]["value"] == 20_000

        # FWA only — GMV scoped to 12_000.
        fwa_resp = await client.get(PATH, headers=headers, params={"city": "fwa"})
        assert fwa_resp.status_code == 200
        assert fwa_resp.json()["kpis"]["gmv_cents"]["value"] == 12_000
        assert fwa_resp.json()["city"] == "fwa"


# ── Heatmap ────────────────────────────────────────────────────────── #


class TestOpsDashboardHeatmap:
    @pytest.mark.asyncio
    async def test_heatmap_shape_is_7x16(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get(PATH, headers=headers)
        assert resp.status_code == 200
        hm = resp.json()["heatmap"]
        assert hm["rows"] == ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        assert hm["hours"] == list(range(7, 23))
        assert len(hm["levels"]) == 7
        assert all(len(row) == 16 for row in hm["levels"])

    @pytest.mark.asyncio
    async def test_heatmap_records_peak_label(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await seed_cities(db_session)
        cust = await _create_user_with_role(
            db_session, "heat-cust@test.com", "Cust", "client"
        )
        det_id, _ = await _make_detailer_in_city(
            db_session, "heat-det@test.com", "fwa"
        )
        svc_id = await _any_service_id(db_session)

        # Two appointments on the same dow/hour bucket inside the last 7d.
        now = datetime.now(timezone.utc)
        # Pick a recent day/hour we know falls in [7..22] UTC.
        bucket = now.replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=2)
        for _ in range(2):
            await _create_appointment(
                db_session,
                client_id=cust.id,
                detailer_id=det_id,
                service_id=svc_id,
                status=AppointmentStatus.COMPLETED,
                scheduled_time=bucket,
                actual_price=10_000,
            )

        headers = await _admin_headers(client, db_session)
        resp = await client.get(PATH, headers=headers, params={"window": "7d"})
        assert resp.status_code == 200
        hm = resp.json()["heatmap"]
        assert hm["peak_label"].endswith("12:00")
