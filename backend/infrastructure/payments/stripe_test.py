"""
infrastructure/payments/stripe_test.py — Stripe test-mode adapter.

Selected when settings.STRIPE_SECRET_KEY is a real sk_test_* key. Hits
the real Stripe API in test mode (4242-4242-4242-4242 cards etc.) and
matches production behaviour bit-for-bit; only the cost differs.

The Stripe SDK is synchronous, so we wrap each call in
asyncio.to_thread to keep the event loop free. The existing
PaymentService follows the same pattern (see
PaymentService._get_or_create_stripe_customer).
"""
from __future__ import annotations

import asyncio
import logging

import stripe

from infrastructure.payments.base import (
    PaymentAdapterError,
    PaymentMethodAdapter,
    PaymentMethodSnapshot,
    SetupIntentResult,
)

logger = logging.getLogger(__name__)


class StripeTestAdapter(PaymentMethodAdapter):
    """Real Stripe SDK with test-mode keys. Same code runs against
    sk_live_* in production — config flip only."""

    async def create_setup_intent(
        self,
        *,
        customer_id: str,
        idempotency_key: str | None = None,
    ) -> SetupIntentResult:
        try:
            si = await asyncio.to_thread(
                stripe.SetupIntent.create,
                customer=customer_id,
                payment_method_types=["card"],
                usage="off_session",  # so we can charge it on future bookings
                idempotency_key=idempotency_key,
            )
        except stripe.error.StripeError as exc:
            logger.warning("stripe.setup_intent.create failed: %s", exc)
            raise PaymentAdapterError(str(exc)) from exc

        return SetupIntentResult(
            setup_intent_id=si.id,
            client_secret=si.client_secret,
            customer_id=customer_id,
        )

    async def detach_payment_method(
        self, *, stripe_payment_method_id: str
    ) -> None:
        try:
            await asyncio.to_thread(
                stripe.PaymentMethod.detach,
                stripe_payment_method_id,
            )
        except stripe.error.InvalidRequestError as exc:
            # Already detached or unknown — Stripe treats it as 4xx; we
            # treat as idempotent success since the local soft-delete is
            # what matters for the user-facing list.
            logger.info(
                "stripe.payment_method.detach 4xx (already detached?): %s",
                exc,
            )
        except stripe.error.StripeError as exc:
            logger.warning("stripe.payment_method.detach failed: %s", exc)
            raise PaymentAdapterError(str(exc)) from exc

    async def fetch_payment_method(
        self, *, stripe_payment_method_id: str
    ) -> PaymentMethodSnapshot:
        try:
            pm = await asyncio.to_thread(
                stripe.PaymentMethod.retrieve,
                stripe_payment_method_id,
            )
        except stripe.error.StripeError as exc:
            logger.warning("stripe.payment_method.retrieve failed: %s", exc)
            raise PaymentAdapterError(str(exc)) from exc

        return _snapshot_from_stripe(pm)


def _snapshot_from_stripe(pm) -> PaymentMethodSnapshot:
    """Translate the Stripe PaymentMethod object into our internal shape.
    Shared with the webhook handler so both code paths agree on the
    field mapping."""
    card = (pm.get("card") or {}) if isinstance(pm, dict) else (
        getattr(pm, "card", None) or {}
    )
    billing = (
        (pm.get("billing_details") or {}) if isinstance(pm, dict)
        else (getattr(pm, "billing_details", None) or {})
    )
    billing_addr = (
        (billing.get("address") or {}) if isinstance(billing, dict)
        else (getattr(billing, "address", None) or {})
    )

    def _g(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    return PaymentMethodSnapshot(
        stripe_payment_method_id=_g(pm, "id"),
        type=_g(pm, "type", "card") or "card",
        brand=_g(card, "brand"),
        last4=_g(card, "last4"),
        exp_month=_g(card, "exp_month"),
        exp_year=_g(card, "exp_year"),
        billing_zip=_g(billing_addr, "postal_code"),
    )
