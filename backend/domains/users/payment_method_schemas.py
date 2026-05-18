"""
domains/users/payment_method_schemas.py — request/response shapes for
`/api/v1/users/me/payment-methods` (Phase 4 chunk U).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas import _BaseRequestSchema, _BaseSchema


class PaymentMethodResponse(_BaseSchema):
    """Saved card / bank as exposed to the client. Stripe is the source
    of truth for the underlying instrument — what lives here is the
    user-visible mirror."""
    id: uuid.UUID
    type: str = "card"
    brand: str | None = None
    last4: str | None = None
    exp_month: int | None = None
    exp_year: int | None = None
    billing_zip: str | None = None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime


class SetupIntentRequest(_BaseRequestSchema):
    """Body for POST /me/payment-methods/setup-intent.

    Intentionally empty today — Stripe's SetupIntent only needs
    customer + payment_method_types, both server-controlled. The shape
    exists so we can add `usage` or `payment_method_types` overrides in
    a future phase without rewriting the endpoint signature."""
    # TODO(phase 5): expose `payment_method_types` override once we add
    # Apple Pay / Google Pay support — for now everything routes through
    # the card flow.


class SetupIntentResponse(_BaseSchema):
    """What the frontend's Stripe SDK consumes to confirm the card."""
    setup_intent_id: str
    client_secret: str
    publishable_key: str = Field(
        ...,
        description="The Stripe publishable key the SDK needs alongside "
                    "the client_secret. Echoed here so the frontend can "
                    "instantiate Stripe.js without a separate /config call.",
    )
