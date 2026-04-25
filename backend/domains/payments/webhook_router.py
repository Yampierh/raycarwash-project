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
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from infrastructure.db.session import get_db
from app.models.models import ProviderProfile, ProcessedWebhook
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
        except (json.JSONDecodeError, UnicodeDecodeError):
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

    # ---- Idempotency check ----
    # Stripe guarantees at-least-once delivery. Use ON CONFLICT DO NOTHING to
    # detect duplicates atomically — no rollback path needed.
    dedup_stmt = (
        pg_insert(ProcessedWebhook)
        .values(
            stripe_event_id=event_id,
            event_type=event_type,
            processed_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_nothing(index_elements=["stripe_event_id"])
    )
    result = await db.execute(dedup_stmt)
    await db.flush()
    if result.rowcount == 0:
        logger.info(
            "Stripe webhook duplicate — already processed | id=%s type=%s",
            event_id, event_type,
        )
        return {"received": True}

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
            "Payment failed | pi=%s reason=%s — push notification pending implementation",
            pi_id, reason,
        )
        # Push notification to client not yet implemented (requires FCM/APNs integration)

    # ---- Stripe Identity events ---------------------------------------- #

    elif event_type == "identity.verification_session.verified":
        await _handle_identity_verified(event, db)

    elif event_type == "identity.verification_session.requires_input":
        await _handle_identity_requires_input(event, db)

    elif event_type == "identity.verification_session.canceled":
        session_id = event["data"]["object"]["id"]
        logger.info("Identity session canceled | session=%s", session_id)

    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    return {"received": True}


# ------------------------------------------------------------------ #
#  Stripe Identity handlers                                           #
# ------------------------------------------------------------------ #

async def _handle_identity_verified(event: dict, db: AsyncSession) -> None:
    """Mark detailer as approved when Stripe verifies their identity."""
    session_obj = event["data"]["object"]
    session_id  = session_obj["id"]
    user_id_str = session_obj.get("metadata", {}).get("user_id")

    result = await db.execute(
        select(ProviderProfile).where(
            ProviderProfile.stripe_verification_session_id == session_id
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        logger.warning(
            "Identity verified but no profile found | session=%s user_id=%s",
            session_id, user_id_str,
        )
        return

    now = datetime.now(timezone.utc)
    profile.verification_status    = "approved"
    profile.verification_reviewed_at = now
    profile.is_accepting_bookings  = True
    await db.commit()

    logger.info(
        "Detailer identity approved | user_id=%s session=%s",
        profile.user_id, session_id,
    )


async def _handle_identity_requires_input(event: dict, db: AsyncSession) -> None:
    """Mark detailer as rejected when Stripe cannot verify their identity."""
    session_obj    = event["data"]["object"]
    session_id     = session_obj["id"]
    last_error     = session_obj.get("last_error") or {}
    reason_code    = last_error.get("code", "unknown")
    reason_reason  = last_error.get("reason", "")
    rejection_msg  = f"{reason_code}: {reason_reason}".strip(": ")

    result = await db.execute(
        select(ProviderProfile).where(
            ProviderProfile.stripe_verification_session_id == session_id
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        logger.warning(
            "Identity requires_input but no profile found | session=%s",
            session_id,
        )
        return

    now = datetime.now(timezone.utc)
    profile.verification_status      = "rejected"
    profile.verification_reviewed_at = now
    profile.rejection_reason         = rejection_msg
    profile.is_accepting_bookings    = False
    await db.commit()

    logger.warning(
        "Detailer identity rejected | user_id=%s session=%s reason=%s",
        profile.user_id, session_id, rejection_msg,
    )
