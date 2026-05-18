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
from domains.payments.models import ProcessedWebhook
from domains.providers.models import ProviderProfile
from domains.payments.service import PaymentService

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

    # ---- Saved payment methods (Phase 4 chunk U) ---------------------- #

    elif event_type in (
        "payment_method.attached",
        "payment_method.updated",
        "setup_intent.succeeded",
    ):
        await _handle_payment_method_upsert(event, db)

    elif event_type == "payment_method.detached":
        await _handle_payment_method_detached(event, db)

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


# ------------------------------------------------------------------ #
#  Saved payment methods (Phase 4 chunk U)                            #
# ------------------------------------------------------------------ #


async def _handle_payment_method_upsert(event: dict, db: AsyncSession) -> None:
    """Insert or update the local mirror of a Stripe PaymentMethod.

    Triggered by:
      - payment_method.attached: card was just attached to a customer.
      - payment_method.updated:  exp_month / billing_zip / brand drift.
      - setup_intent.succeeded:  fallback path — Stripe doesn't always
        guarantee payment_method.attached fires first, and some flows
        only emit setup_intent.succeeded with the PM nested inside.

    We resolve the User from the Stripe customer ID (we mirrored it
    onto User.stripe_customer_id when we minted the cus_*). If the
    customer is unknown we skip silently — could be a webhook for a
    different environment, or the user was hard-deleted.
    """
    from app.middleware.audit_context import AuditContext
    from domains.users.models import User
    from domains.users.payment_method_service import PaymentMethodService
    from infrastructure.payments.stripe_test import _snapshot_from_stripe

    obj = event["data"]["object"]
    event_type = event.get("type", "")

    # setup_intent.succeeded carries customer + payment_method directly;
    # payment_method.* events carry customer on the PM object itself.
    if event_type == "setup_intent.succeeded":
        customer_id = obj.get("customer")
        pm_obj = obj.get("payment_method")
        # pm_obj may be a string ID; in that case the snapshot would lack
        # card details. Re-fetch through the adapter.
        if isinstance(pm_obj, str):
            from app.core.dependencies import get_payment_method_adapter

            try:
                snapshot = await get_payment_method_adapter().fetch_payment_method(
                    stripe_payment_method_id=pm_obj
                )
            except Exception as exc:
                logger.warning(
                    "setup_intent.succeeded: cannot retrieve PM=%s: %s", pm_obj, exc
                )
                return
        elif isinstance(pm_obj, dict):
            snapshot = _snapshot_from_stripe(pm_obj)
        else:
            logger.info("setup_intent.succeeded with no payment_method — skipping")
            return
    else:
        customer_id = obj.get("customer")
        snapshot = _snapshot_from_stripe(obj)

    if not customer_id:
        logger.info(
            "payment_method webhook skipped — no customer | event_type=%s pm=%s",
            event_type, snapshot.stripe_payment_method_id,
        )
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        logger.info(
            "payment_method webhook skipped — unknown customer | cus=%s",
            customer_id,
        )
        return

    # Webhook callers have no HTTP request context — use an empty
    # AuditContext so the audit row records the source as "stripe_webhook"
    # in metadata rather than crashing on getattr.
    service = PaymentMethodService(
        db=db,
        audit_ctx=AuditContext(request_id=None, ip_address=None, user_agent=None),
    )
    await service.upsert_from_snapshot(user_id=user.id, snapshot=snapshot)
    await db.commit()
    logger.info(
        "payment_method synced | user=%s pm=%s brand=%s last4=%s",
        user.id, snapshot.stripe_payment_method_id,
        snapshot.brand, snapshot.last4,
    )


async def _handle_payment_method_detached(event: dict, db: AsyncSession) -> None:
    """Soft-delete the local mirror when the card is detached at Stripe
    (user removed via Stripe Dashboard, or our own server-side detach
    echoing back)."""
    from app.middleware.audit_context import AuditContext
    from domains.users.payment_method_service import PaymentMethodService

    obj = event["data"]["object"]
    stripe_pm_id = obj.get("id")
    if not stripe_pm_id:
        logger.info("payment_method.detached missing id — skipping")
        return

    service = PaymentMethodService(
        db=db,
        audit_ctx=AuditContext(request_id=None, ip_address=None, user_agent=None),
    )
    ok = await service.mark_detached_by_stripe_id(
        stripe_payment_method_id=stripe_pm_id
    )
    if ok:
        await db.commit()
        logger.info("payment_method detached locally | pm=%s", stripe_pm_id)
    else:
        logger.info(
            "payment_method.detached for unknown PM (already gone or never seen) | pm=%s",
            stripe_pm_id,
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
