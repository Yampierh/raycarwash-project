"""
tests/test_promo_lookup_and_preview.py — Plan 24 C-2.

Covers:
  - GET  /api/v1/promo/{code}
  - POST /api/v1/promo/preview

Scenarios:
  - NEW10 lookup anonymous (no eligibility fields)
  - NEW10 lookup authenticated (eligible + remaining_per_user populated)
  - 404 on unknown code
  - Case-insensitive lookup (lower / mixed / padded)
  - Inactive promo → not eligible
  - Expired promo → not eligible
  - max_redemptions_per_user reached → not eligible (after seeding a redemption)
  - Preview: anonymous + with subtotal
  - Preview: below_min_order
  - Preview: percent discount math
  - Preview: discount cap to subtotal (subtotal < fixed_cents discount)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seed_promos import seed_promos
from domains.promos.models import AppliedPromoCode, PromoCode
from tests.conftest import _create_user_with_role, get_access_token


LOOKUP_PATH = "/api/v1/promo/{code}"
PREVIEW_PATH = "/api/v1/promo/preview"


# ── Helpers ────────────────────────────────────────────────────────── #


async def _client_headers(client: AsyncClient, db: AsyncSession, email: str) -> dict:
    await _create_user_with_role(db, email, "C " + email, "client")
    token = await get_access_token(client, email)
    return {"Authorization": f"Bearer {token}"}


async def _seed_new10(db: AsyncSession) -> PromoCode:
    """Ensure the canonical NEW10 promo exists. conftest doesn't run
    seed_promos on every test — so we run it here on-demand."""
    await seed_promos(db)
    return (await db.execute(
        select(PromoCode).where(PromoCode.code == "NEW10")
    )).scalar_one()


async def _add_promo(
    db: AsyncSession,
    *,
    code: str,
    discount_type: str = "fixed_cents",
    discount_amount: int = 1_000,
    min_order_cents: int | None = None,
    max_redemptions_per_user: int = 1,
    is_active: bool = True,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> PromoCode:
    promo = PromoCode(
        code=code,
        description=f"Test {code}",
        discount_type=discount_type,
        discount_amount=discount_amount,
        min_order_cents=min_order_cents,
        max_redemptions_per_user=max_redemptions_per_user,
        is_active=is_active,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return promo


# ── Anonymous lookup ──────────────────────────────────────────────── #


class TestAnonymousLookup:
    @pytest.mark.asyncio
    async def test_new10_anon(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_new10(db_session)
        resp = await client.get(LOOKUP_PATH.format(code="NEW10"))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["code"] == "NEW10"
        assert data["discount_type"] == "fixed_cents"
        assert data["discount_amount"] == 1_000
        # Anonymous → eligibility fields are not computed
        assert data["eligible"] is None
        assert data["remaining_per_user"] is None
        # And the global state is fine
        assert data["ineligible_reason"] is None

    @pytest.mark.asyncio
    async def test_unknown_code_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        resp = await client.get(LOOKUP_PATH.format(code="NOPENOPE"))
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_case_insensitive_lookup(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_new10(db_session)
        for variant in ("new10", "New10", " NEW10 "):
            resp = await client.get(LOOKUP_PATH.format(code=variant))
            assert resp.status_code == 200
            assert resp.json()["data"]["code"] == "NEW10"


# ── Inactive / expired promos ─────────────────────────────────────── #


class TestPromoLifecycle:
    @pytest.mark.asyncio
    async def test_inactive_promo_marked(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _add_promo(db_session, code="OFFTEST", is_active=False)
        resp = await client.get(LOOKUP_PATH.format(code="OFFTEST"))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["ineligible_reason"] == "inactive"

    @pytest.mark.asyncio
    async def test_expired_promo(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        past = datetime.now(timezone.utc) - timedelta(days=10)
        await _add_promo(
            db_session, code="OLDTEST",
            valid_until=past,
        )
        resp = await client.get(LOOKUP_PATH.format(code="OLDTEST"))
        data = resp.json()["data"]
        assert data["ineligible_reason"] == "expired"

    @pytest.mark.asyncio
    async def test_future_promo(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        await _add_promo(
            db_session, code="SOONTEST",
            valid_from=future,
        )
        resp = await client.get(LOOKUP_PATH.format(code="SOONTEST"))
        data = resp.json()["data"]
        assert data["ineligible_reason"] == "not_yet_valid"


# ── Authenticated lookup ──────────────────────────────────────────── #


class TestAuthenticatedLookup:
    @pytest.mark.asyncio
    async def test_first_time_user_eligible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_new10(db_session)
        headers = await _client_headers(client, db_session, "first@test.com")
        resp = await client.get(LOOKUP_PATH.format(code="NEW10"), headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["eligible"] is True
        assert data["remaining_per_user"] == 1
        assert data["ineligible_reason"] is None

    @pytest.mark.asyncio
    async def test_after_redemption_not_eligible(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        promo = await _seed_new10(db_session)
        headers = await _client_headers(client, db_session, "second@test.com")
        # Manually insert a redemption row for this user
        user = await _create_user_with_role(db_session, "second-redeemer@test.com", "X", "client")
        # Insert via the user we'll authenticate as — look them up
        from domains.users.models import User as UserModel
        actual = (await db_session.execute(
            select(UserModel).where(UserModel.email == "second@test.com")
        )).scalar_one()
        db_session.add(AppliedPromoCode(
            promo_code_id=promo.id,
            user_id=actual.id,
            appointment_id=None,
            amount_discounted_cents=1_000,
            applied_at=datetime.now(timezone.utc),
        ))
        await db_session.commit()

        resp = await client.get(LOOKUP_PATH.format(code="NEW10"), headers=headers)
        data = resp.json()["data"]
        assert data["eligible"] is False
        assert data["remaining_per_user"] == 0
        assert data["ineligible_reason"] == "max_redemptions_per_user_reached"


# ── Preview ───────────────────────────────────────────────────────── #


class TestPreview:
    @pytest.mark.asyncio
    async def test_preview_anonymous_happy(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_new10(db_session)
        resp = await client.post(
            PREVIEW_PATH,
            json={"code": "NEW10", "subtotal_cents": 5_000},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["eligible"] is True
        assert data["discount_cents"] == 1_000
        assert data["final_cents"] == 4_000
        assert data["reason"] is None

    @pytest.mark.asyncio
    async def test_preview_below_min_order(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _seed_new10(db_session)
        # NEW10 requires subtotal >= 2000¢; send 1000
        resp = await client.post(
            PREVIEW_PATH,
            json={"code": "NEW10", "subtotal_cents": 1_000},
        )
        data = resp.json()["data"]
        assert data["eligible"] is False
        assert data["reason"] == "below_min_order"
        assert data["discount_cents"] == 0
        assert data["final_cents"] == 1_000

    @pytest.mark.asyncio
    async def test_preview_percent_math(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _add_promo(
            db_session, code="PERC25",
            discount_type="percent",
            discount_amount=25,
        )
        resp = await client.post(
            PREVIEW_PATH,
            json={"code": "PERC25", "subtotal_cents": 10_000},
        )
        data = resp.json()["data"]
        assert data["discount_cents"] == 2_500
        assert data["final_cents"] == 7_500

    @pytest.mark.asyncio
    async def test_preview_caps_discount_to_subtotal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Fixed $10 discount but subtotal only $5 → discount caps to $5
        await _add_promo(
            db_session, code="CAP10",
            discount_amount=1_000,
            min_order_cents=None,
        )
        resp = await client.post(
            PREVIEW_PATH,
            json={"code": "CAP10", "subtotal_cents": 500},
        )
        data = resp.json()["data"]
        assert data["discount_cents"] == 500
        assert data["final_cents"] == 0

    @pytest.mark.asyncio
    async def test_preview_unknown_code(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        resp = await client.post(
            PREVIEW_PATH,
            json={"code": "GHOST", "subtotal_cents": 5_000},
        )
        # 200 with eligible=false rather than 404 — preview is a calc
        # endpoint, not a lookup. Treating unknown codes as ineligible
        # lets the frontend render "Invalid code" inline without a try/catch.
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["eligible"] is False
        assert data["reason"] == "not_found"

    @pytest.mark.asyncio
    async def test_preview_inactive_promo(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _add_promo(db_session, code="DISABLED", is_active=False)
        resp = await client.post(
            PREVIEW_PATH,
            json={"code": "DISABLED", "subtotal_cents": 5_000},
        )
        data = resp.json()["data"]
        assert data["eligible"] is False
        assert data["reason"] == "inactive"


# ── Seed idempotency smoke ─────────────────────────────────────────── #


class TestSeed:
    @pytest.mark.asyncio
    async def test_seed_is_idempotent(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await seed_promos(db_session)
        await seed_promos(db_session)  # second call must not duplicate
        count = (await db_session.execute(
            select(PromoCode).where(PromoCode.code == "NEW10")
        )).scalars().all()
        assert len(count) == 1
