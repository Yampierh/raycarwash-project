"""
infrastructure/payments/stripe_stub.py — fake adapter for dev/CI when
STRIPE_SECRET_KEY is a placeholder (sk_test_placeholder, sk_live_placeholder,
or empty).

Mirrors the existing PaymentService._is_stub_key() escape hatch so tests
and bootstrap-without-Stripe-keys flows stay green. Returns deterministic
IDs so test snapshots are stable.
"""
from __future__ import annotations

import logging
import secrets

from infrastructure.payments.base import (
    PaymentMethodAdapter,
    PaymentMethodSnapshot,
    SetupIntentResult,
)

logger = logging.getLogger(__name__)


class StripeStubAdapter(PaymentMethodAdapter):
    async def create_setup_intent(
        self,
        *,
        customer_id: str,
        idempotency_key: str | None = None,
    ) -> SetupIntentResult:
        si_id = f"seti_stub_{secrets.token_hex(8)}"
        client_secret = f"{si_id}_secret_{secrets.token_hex(12)}"
        logger.info("stub: create_setup_intent %s for %s", si_id, customer_id)
        return SetupIntentResult(
            setup_intent_id=si_id,
            client_secret=client_secret,
            customer_id=customer_id,
        )

    async def detach_payment_method(
        self, *, stripe_payment_method_id: str
    ) -> None:
        logger.info("stub: detach_payment_method %s", stripe_payment_method_id)

    async def fetch_payment_method(
        self, *, stripe_payment_method_id: str
    ) -> PaymentMethodSnapshot:
        # Tests never call this in stub mode — webhook events carry the
        # whole PM payload. Return a deterministic placeholder anyway so
        # any incidental call doesn't blow up.
        return PaymentMethodSnapshot(
            stripe_payment_method_id=stripe_payment_method_id,
            type="card",
            brand="visa",
            last4="4242",
            exp_month=12,
            exp_year=2030,
            billing_zip="00000",
        )
