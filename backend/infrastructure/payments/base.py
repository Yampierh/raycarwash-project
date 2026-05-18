"""
infrastructure/payments/base.py — PaymentMethodAdapter Protocol (ADR-008
addendum for Phase 4 chunk U).

The adapter wraps the Stripe operations Phase 4 needs for saved payment
methods. Two implementations:

  - StripeTestAdapter — uses the real Stripe SDK with sk_test_* keys.
    Selected by app/core/dependencies.get_payment_method_adapter()
    when settings.STRIPE_SECRET_KEY starts with sk_test_.
  - StripeStubAdapter — used when STRIPE_SECRET_KEY is a placeholder
    (the existing dev/CI behaviour from PaymentService). Returns
    deterministic fake IDs so tests don't need network access.

The Protocol stays small on purpose. Anything that mutates a card
(detach, set as default for invoicing, etc.) goes through here so the
service layer never imports `stripe` directly — keeps Stripe SDK churn
contained to a single file when we upgrade.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class PaymentAdapterError(Exception):
    """Generic adapter failure — transport, Stripe-side 5xx, etc.
    The service translates this into 502 Bad Gateway so the user sees
    "payment provider unavailable" instead of a leaked traceback."""


@dataclass(frozen=True)
class SetupIntentResult:
    """Minimum shape the frontend needs to confirm a new card via the
    Stripe SDK."""
    setup_intent_id: str
    client_secret: str
    customer_id: str


@dataclass(frozen=True)
class PaymentMethodSnapshot:
    """Stripe payment method as we mirror it locally. Only non-PCI fields."""
    stripe_payment_method_id: str
    type: str            # "card" | "us_bank_account" | "apple_pay" | ...
    brand: str | None    # "visa", "mastercard", ...
    last4: str | None
    exp_month: int | None
    exp_year: int | None
    billing_zip: str | None


class PaymentMethodAdapter(Protocol):
    """Operations Phase 4 chunk U needs against Stripe Customers + Payment
    Methods. Webhook-side reads (payment_method.attached event payloads)
    can use the dict directly — we don't model those here because the
    webhook router already lives outside the service layer."""

    async def create_setup_intent(
        self,
        *,
        customer_id: str,
        idempotency_key: str | None = None,
    ) -> SetupIntentResult:
        """Create a Stripe SetupIntent so the frontend's Stripe SDK can
        collect card details and attach the PM to the customer."""

    async def detach_payment_method(
        self, *, stripe_payment_method_id: str
    ) -> None:
        """Server-side detach. Webhook payment_method.detached fires and
        the service mirrors the soft-delete locally."""

    async def fetch_payment_method(
        self, *, stripe_payment_method_id: str
    ) -> PaymentMethodSnapshot:
        """Refetch a PM by ID — used to re-sync after webhook delivery
        gaps or to backfill state we may have missed during outages.

        Raises PaymentAdapterError if Stripe responds 4xx/5xx (or no
        such ID). Caller decides whether to soft-delete the local mirror
        on 4xx (PM was revoked at Stripe) or retry on 5xx."""
