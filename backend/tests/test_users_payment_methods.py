"""
tests/test_users_payment_methods.py — Phase 4 chunk U.

Covers /api/v1/users/me/payment-methods endpoints + webhook handlers +
the payment_methods block in the Profile Hub.

The Stripe adapter is patched to a stub that returns deterministic IDs
so tests don't need network access. Real Stripe-mode behaviour is
identical (PaymentService._is_stub_key picks the stub when keys are
placeholders).
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.users.models import User
from domains.users.payment_method import PaymentMethod
from infrastructure.payments.base import (
    PaymentMethodSnapshot,
    SetupIntentResult,
)


# ─── helpers ──────────────────────────────────────────────────────────────────


async def _login(client: AsyncClient, email: str = "pm@test.com") -> str:
    reg = await client.post(
        "/auth/register",
        json={"email": email, "password": "Secure1234!"},
    )
    assert reg.status_code == 201, reg.text
    onboarding = reg.json()["onboarding_token"]
    phone_suffix = str(abs(hash(email)) % 10_000_000).zfill(7)
    await client.put(
        "/auth/complete-profile",
        json={"full_name": "PM Tester", "phone_number": f"+155{phone_suffix}"},
        headers={"Authorization": f"Bearer {onboarding}"},
    )
    login = await client.post(
        "/auth/login", json={"email": email, "password": "Secure1234!"},
    )
    return login.json()["access_token"]


async def _get_user(db_session: AsyncSession, email: str) -> User:
    return (
        await db_session.execute(select(User).where(User.email == email))
    ).scalar_one()


@pytest.fixture
def stub_adapter(monkeypatch):
    """Replace the PaymentMethodAdapter at its use-site (the service
    module's `get_payment_method_adapter` binding). Patching the deps
    module alone wouldn't help — the service caches the resolved
    callable on import."""
    from domains.users import payment_method_service as svc_mod

    fake = AsyncMock()
    fake.create_setup_intent = AsyncMock(
        return_value=SetupIntentResult(
            setup_intent_id="seti_test_abc123",
            client_secret="seti_test_abc123_secret_xyz",
            customer_id="cus_test_xyz",
        )
    )
    fake.detach_payment_method = AsyncMock(return_value=None)
    fake.fetch_payment_method = AsyncMock(
        return_value=PaymentMethodSnapshot(
            stripe_payment_method_id="pm_test_fetched",
            type="card",
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2030,
            billing_zip="46201",
        )
    )

    monkeypatch.setattr(
        svc_mod, "get_payment_method_adapter", lambda: fake,
    )
    return fake


# ─── Setup intent (step-up gated) ─────────────────────────────────────────────


async def _expire_step_up(db_session: AsyncSession, email: str) -> None:
    """Expire step-up by mutating the in-memory User entity, not a raw
    UPDATE. The raw UPDATE bypasses SQLAlchemy's identity map, leaving
    the cached User instance that get_current_user later reads with the
    stale last_step_up_at value — so step-up would falsely pass."""
    user = await _get_user(db_session, email)
    user.last_step_up_at = None
    await db_session.commit()


@pytest.mark.asyncio
async def test_setup_intent_requires_step_up(
    client: AsyncClient, stub_adapter, db_session: AsyncSession,
) -> None:
    token = await _login(client, "pm-nostep@test.com")
    # Login already populates step-up window (post-H3). Expire it to
    # exercise the rejection path.
    await _expire_step_up(db_session, "pm-nostep@test.com")

    resp = await client.post(
        "/api/v1/users/me/payment-methods/setup-intent",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "step_up_required"
    stub_adapter.create_setup_intent.assert_not_awaited()


@pytest.mark.asyncio
async def test_setup_intent_returns_client_secret(
    client: AsyncClient, stub_adapter,
) -> None:
    """Happy path: a freshly logged-in user is inside the step-up
    window thanks to Hotfix H3, so the SetupIntent fires."""
    token = await _login(client, "pm-ok@test.com")
    resp = await client.post(
        "/api/v1/users/me/payment-methods/setup-intent",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["setup_intent_id"] == "seti_test_abc123"
    assert data["client_secret"].startswith("seti_test_abc123_secret")
    assert data["publishable_key"]  # whatever the env config supplies


@pytest.mark.asyncio
async def test_setup_intent_forwards_idempotency_key_to_adapter(
    client: AsyncClient, stub_adapter,
) -> None:
    token = await _login(client, "pm-idem@test.com")
    await client.post(
        "/api/v1/users/me/payment-methods/setup-intent",
        json={},
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": "client-supplied-key-abc",
        },
    )
    assert stub_adapter.create_setup_intent.await_args.kwargs[
        "idempotency_key"
    ] == "client-supplied-key-abc"


# ─── Webhook upsert ──────────────────────────────────────────────────────────


def _attached_event(stripe_pm_id: str, customer_id: str, last4: str = "4242") -> dict:
    return {
        "id": f"evt_test_{stripe_pm_id}",
        "type": "payment_method.attached",
        "data": {
            "object": {
                "id": stripe_pm_id,
                "type": "card",
                "customer": customer_id,
                "card": {
                    "brand": "visa",
                    "last4": last4,
                    "exp_month": 8,
                    "exp_year": 2030,
                },
                "billing_details": {"address": {"postal_code": "46201"}},
            }
        },
    }


@pytest.mark.asyncio
async def test_webhook_attached_creates_local_mirror_and_auto_defaults(
    client: AsyncClient, stub_adapter, db_session: AsyncSession,
) -> None:
    token = await _login(client, "pm-webhook@test.com")
    user = await _get_user(db_session, "pm-webhook@test.com")

    # Mint a SetupIntent so user.stripe_customer_id gets populated by
    # PaymentService._get_or_create_stripe_customer.
    await client.post(
        "/api/v1/users/me/payment-methods/setup-intent",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    await db_session.refresh(user)
    customer_id = user.stripe_customer_id
    assert customer_id is not None

    # Deliver the webhook.
    resp = await client.post(
        "/webhooks/stripe",
        content=json.dumps(_attached_event("pm_test_first", customer_id)),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text

    # List endpoint should now report the card AND it should be default
    # (first card per user).
    listing = await client.get(
        "/api/v1/users/me/payment-methods",
        headers={"Authorization": f"Bearer {token}"},
    )
    items = listing.json()["data"]
    assert len(items) == 1
    assert items[0]["brand"] == "visa"
    assert items[0]["last4"] == "4242"
    assert items[0]["is_default"] is True


@pytest.mark.asyncio
async def test_webhook_attached_is_idempotent_on_replay(
    client: AsyncClient, stub_adapter, db_session: AsyncSession,
) -> None:
    """Stripe at-least-once delivery — a replayed event must not create
    a duplicate row. ProcessedWebhook + ON CONFLICT DO NOTHING handle
    the dedup; we just want to assert the user-facing list reflects it."""
    token = await _login(client, "pm-replay@test.com")
    user = await _get_user(db_session, "pm-replay@test.com")
    await client.post(
        "/api/v1/users/me/payment-methods/setup-intent",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    await db_session.refresh(user)
    customer_id = user.stripe_customer_id

    payload = _attached_event("pm_test_replay", customer_id)
    for _ in range(3):
        resp = await client.post(
            "/webhooks/stripe",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200, resp.text

    rows = (await db_session.execute(
        select(PaymentMethod).where(
            PaymentMethod.user_id == user.id,
            PaymentMethod.is_deleted.is_(False),
        )
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_webhook_detached_soft_deletes_local_row(
    client: AsyncClient, stub_adapter, db_session: AsyncSession,
) -> None:
    token = await _login(client, "pm-detach@test.com")
    user = await _get_user(db_session, "pm-detach@test.com")
    await client.post(
        "/api/v1/users/me/payment-methods/setup-intent",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    await db_session.refresh(user)
    customer_id = user.stripe_customer_id

    await client.post(
        "/webhooks/stripe",
        content=json.dumps(_attached_event("pm_test_kill", customer_id)),
        headers={"Content-Type": "application/json"},
    )

    detached = {
        "id": "evt_test_detach",
        "type": "payment_method.detached",
        "data": {"object": {"id": "pm_test_kill"}},
    }
    resp = await client.post(
        "/webhooks/stripe",
        content=json.dumps(detached),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text

    listing = await client.get(
        "/api/v1/users/me/payment-methods",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert listing.json()["data"] == []


# ─── Default flipping + delete ───────────────────────────────────────────────


async def _attach_card(
    client: AsyncClient,
    db_session: AsyncSession,
    token: str,
    email: str,
    stripe_pm_id: str,
    last4: str = "4242",
) -> str:
    """Helper: mint customer, deliver attached webhook, return local PM id."""
    user = await _get_user(db_session, email)
    if user.stripe_customer_id is None:
        await client.post(
            "/api/v1/users/me/payment-methods/setup-intent",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        await db_session.refresh(user)
    await client.post(
        "/webhooks/stripe",
        content=json.dumps(_attached_event(stripe_pm_id, user.stripe_customer_id, last4)),
        headers={"Content-Type": "application/json"},
    )
    listing = await client.get(
        "/api/v1/users/me/payment-methods",
        headers={"Authorization": f"Bearer {token}"},
    )
    items = listing.json()["data"]
    for item in items:
        if item["last4"] == last4:
            return item["id"]
    raise AssertionError(f"card with last4={last4} not found")


@pytest.mark.asyncio
async def test_set_default_atomic_only_one_remains(
    client: AsyncClient, stub_adapter, db_session: AsyncSession,
) -> None:
    token = await _login(client, "pm-default@test.com")
    await _attach_card(client, db_session, token, "pm-default@test.com", "pm_a", "1111")
    pm_b = await _attach_card(client, db_session, token, "pm-default@test.com", "pm_b", "2222")

    resp = await client.patch(
        f"/api/v1/users/me/payment-methods/{pm_b}/default",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["is_default"] is True

    rows = (await db_session.execute(
        select(PaymentMethod).where(
            PaymentMethod.is_default.is_(True),
            PaymentMethod.is_deleted.is_(False),
        )
    )).scalars().all()
    assert len(rows) == 1
    assert str(rows[0].id) == pm_b


@pytest.mark.asyncio
async def test_delete_default_promotes_next_and_calls_stripe_detach(
    client: AsyncClient, stub_adapter, db_session: AsyncSession,
) -> None:
    token = await _login(client, "pm-promote@test.com")
    pm_first = await _attach_card(
        client, db_session, token, "pm-promote@test.com", "pm_first", "1111"
    )
    pm_second = await _attach_card(
        client, db_session, token, "pm-promote@test.com", "pm_second", "2222"
    )

    delete = await client.delete(
        f"/api/v1/users/me/payment-methods/{pm_first}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete.status_code == 204, delete.text

    stub_adapter.detach_payment_method.assert_awaited_once_with(
        stripe_payment_method_id="pm_first"
    )

    listing = await client.get(
        "/api/v1/users/me/payment-methods",
        headers={"Authorization": f"Bearer {token}"},
    )
    items = listing.json()["data"]
    assert len(items) == 1
    assert items[0]["id"] == pm_second
    assert items[0]["is_default"] is True


@pytest.mark.asyncio
async def test_delete_requires_step_up(
    client: AsyncClient, stub_adapter, db_session: AsyncSession,
) -> None:
    token = await _login(client, "pm-deletenostep@test.com")
    pm_id = await _attach_card(
        client, db_session, token, "pm-deletenostep@test.com", "pm_delcheck"
    )

    # Expire step-up.
    await _expire_step_up(db_session, "pm-deletenostep@test.com")

    resp = await client.delete(
        f"/api/v1/users/me/payment-methods/{pm_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "step_up_required"
    stub_adapter.detach_payment_method.assert_not_awaited()


@pytest.mark.asyncio
async def test_cross_user_get_returns_404(
    client: AsyncClient, stub_adapter, db_session: AsyncSession,
) -> None:
    alice = await _login(client, "alice-pm@test.com")
    bob = await _login(client, "bob-pm@test.com")
    alice_pm_id = await _attach_card(
        client, db_session, alice, "alice-pm@test.com", "pm_alice"
    )

    resp = await client.get(
        f"/api/v1/users/me/payment-methods/{alice_pm_id}",
        headers={"Authorization": f"Bearer {bob}"},
    )
    assert resp.status_code == 404


# ─── Profile Hub integration ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hub_payment_methods_block_includes_attached_card(
    client: AsyncClient, stub_adapter, db_session: AsyncSession,
) -> None:
    token = await _login(client, "pm-hub@test.com")
    await _attach_card(client, db_session, token, "pm-hub@test.com", "pm_hub")

    resp = await client.get(
        "/api/v1/users/me?include=payment_methods",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    methods = body["data"]["payment_methods"]
    assert len(methods) == 1
    assert methods[0]["brand"] == "visa"
    assert methods[0]["last4"] == "4242"
    assert methods[0]["is_default"] is True
    assert "payment_methods" in (body["meta"].get("includes") or [])
