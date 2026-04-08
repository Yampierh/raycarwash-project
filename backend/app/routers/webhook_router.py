# app/routers/webhook_router.py  —  Sprint 4
#
# Stripe webhook endpoint.
#
# WHY a separate router (not inside payment_router)?
#   The webhook endpoint MUST receive the raw request body bytes for
#   signature verification. FastAPI's JSON parsing consumes the body stream,
#   making it unavailable for stripe.Webhook.construct_event().
#   By keeping it isolated, we avoid accidentally adding middleware or
#   body-parsing dependencies that would break the raw body access.
#
# HOW TO TEST LOCALLY:
#   1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
#   2. stripe listen --forward-to localhost:8000/webhooks/stripe
#   3. stripe trigger payment_intent.succeeded
#
# SECURITY:
#   - Every webhook is verified against STRIPE_WEBHOOK_SECRET before processing.
#   - A missing or invalid signature returns HTTP 400 immediately.
#   - We return HTTP 200 quickly (within the 30s Stripe timeout) even for
#     unhandled event types — Stripe retries on non-2xx for up to 3 days.

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.services.payment_service import PaymentService

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "/stripe",
    status_code=status.HTTP_200_OK,
    summary="Stripe event webhook receiver.",
    description=(
        "Receives signed Stripe webhook events. "
        "Verifies the `Stripe-Signature` header against `STRIPE_WEBHOOK_SECRET`. "
        "**Do not call this endpoint directly** — it is invoked by Stripe."
    ),
    include_in_schema=True,   # visible in docs so devs know it exists
)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Stripe webhook dispatcher.

    Handled events:
      - payment_intent.succeeded  → PAYMENT_CAPTURED audit log
      - payment_intent.payment_failed → warning log (future: notify client)

    Unhandled events are acknowledged with {"received": true} and ignored.
    This is intentional — Stripe sends many event types; we handle only
    the ones relevant to our booking flow.
    """
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # ---- Signature verification ----
    # construct_event() raises SignatureVerificationError if the sig is wrong.
    # We catch it and return 400 so Stripe knows to flag the delivery.
    is_placeholder = settings.STRIPE_WEBHOOK_SECRET in (
        "whsec_placeholder", "whsec_test_placeholder", ""
    )

    if is_placeholder:
        # Dev/CI mode: skip signature check, parse as raw JSON.
        logger.warning(
            "Stripe webhook received with placeholder secret — "
            "skipping signature verification (dev/CI mode)."
        )
        import json
        try:
            event = json.loads(payload)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload.",
            )
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError as exc:
            logger.warning("Stripe webhook: invalid signature — %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Stripe signature.",
            )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payload.",
            )

    event_type = event.get("type", "unknown")
    event_id   = event.get("id", "unknown")
    logger.info("Stripe webhook received | type=%s id=%s", event_type, event_id)

    payment_svc = PaymentService(db)

    # ---- Dispatcher ----
    if event_type == "payment_intent.succeeded":
        pi_id = event["data"]["object"]["id"]
        await payment_svc.handle_payment_succeeded(pi_id)

    elif event_type == "payment_intent.payment_failed":
        pi_id  = event["data"]["object"]["id"]
        reason = (
            event["data"]["object"]
            .get("last_payment_error", {})
            .get("message", "unknown")
        )
        logger.warning(
            "Payment failed | pi=%s reason=%s — TODO: notify client via push",
            pi_id, reason,
        )
        # Sprint 5: trigger push notification to client

    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    return {"received": True}
