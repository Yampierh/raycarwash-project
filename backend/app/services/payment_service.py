# app/services/payment_service.py  —  Sprint 4
#
# CHANGES vs Sprint 3:
#   - TODO_STRIPE blocks replaced with real stripe SDK calls.
#     stripe>=5.0 supports async natively via asyncio.to_thread wrappers
#     (backwards-compatible with all stripe>=11 as well).
#   - create_refund()  — cancellation-policy-driven Stripe refund.
#   - _get_or_create_stripe_customer() — extracted helper.
#
# DESIGN: stripe SDK calls are wrapped in asyncio.to_thread() to keep
# the FastAPI event loop unblocked. stripe>=5.0 also provides native
# async methods (e.g. stripe.PaymentIntent.create_async()), but
# asyncio.to_thread is universally compatible across SDK versions.

from __future__ import annotations

import asyncio
import logging
import uuid

import stripe
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import Appointment, AppointmentStatus, AuditAction, User
from app.repositories.audit_repository import AuditRepository

logger   = logging.getLogger(__name__)
settings = get_settings()


class PaymentService:

    def __init__(self, db: AsyncSession) -> None:
        self._db         = db
        self._audit_repo = AuditRepository(db)

    # ---------------------------------------------------------------- #
    #  Internal helpers                                                 #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _is_stub_key() -> bool:
        """True when running with the placeholder Stripe key (dev/test)."""
        return settings.STRIPE_SECRET_KEY in (
            "sk_test_placeholder", "sk_live_placeholder", ""
        )

    async def _get_or_create_stripe_customer(self, actor: User) -> str:
        """
        Ensure the User has a Stripe Customer ID. Creates one on first call.
        Returns the Stripe cus_xxx string.
        """
        if actor.stripe_customer_id:
            return actor.stripe_customer_id

        if self._is_stub_key():
            stub_cus = f"cus_stub_{actor.id.hex[:16]}"
            actor.stripe_customer_id = stub_cus
            await self._db.flush()
            return stub_cus

        stripe.api_key = settings.STRIPE_SECRET_KEY
        customer = await asyncio.to_thread(
            stripe.Customer.create,
            email=actor.email,
            name=actor.full_name,
            metadata={"raycarwash_user_id": str(actor.id)},
        )
        actor.stripe_customer_id = customer.id
        await self._db.flush()
        logger.info("Stripe Customer created | user=%s cus=%s", actor.id, customer.id)
        return customer.id

    # ---------------------------------------------------------------- #
    #  create_payment_intent                                            #
    # ---------------------------------------------------------------- #

    async def create_payment_intent(
        self,
        appointment_id: uuid.UUID,
        actor: User,
    ) -> dict:
        """
        Create a Stripe PaymentIntent for an appointment and return
        the client_secret to the frontend.

        FLOW:
          1. Load the appointment and validate it's in CONFIRMED state.
          2. Ensure the actor is the CLIENT on the appointment.
          3. Ensure or create the Stripe Customer for this user.
          4. Create a PaymentIntent for estimated_price cents.
          5. Persist stripe_payment_intent_id on the Appointment.
          6. Return {client_secret, payment_intent_id, amount_cents}.

        IDEMPOTENCY:
        If stripe_payment_intent_id is already set, return the existing intent
        (re-fetched from Stripe) without creating a duplicate charge.
        """
        stmt = select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        appointment = result.scalar_one_or_none()

        if appointment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment {appointment_id} not found.",
            )

        if appointment.client_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the booking client can initiate payment.",
            )

        if appointment.status != AppointmentStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Payment can only be initiated for CONFIRMED appointments. "
                    f"Current status: '{appointment.status.value}'."
                ),
            )

        # ---- Idempotency: return existing intent ----
        if appointment.stripe_payment_intent_id:
            existing_pi_id = appointment.stripe_payment_intent_id

            if self._is_stub_key() or existing_pi_id.startswith("pi_stub"):
                return {
                    "payment_intent_id": existing_pi_id,
                    "client_secret": f"{existing_pi_id}_secret_stub",
                    "amount_cents": appointment.estimated_price,
                    "currency": settings.STRIPE_CURRENCY,
                    "status": "requires_payment_method",
                }

            stripe.api_key = settings.STRIPE_SECRET_KEY
            existing_intent = await asyncio.to_thread(
                stripe.PaymentIntent.retrieve, existing_pi_id
            )
            logger.info(
                "Returning existing PaymentIntent | appointment=%s pi=%s",
                appointment_id, existing_pi_id,
            )
            return {
                "payment_intent_id": existing_intent.id,
                "client_secret": existing_intent.client_secret,
                "amount_cents": existing_intent.amount,
                "currency": existing_intent.currency,
                "status": existing_intent.status,
            }

        # ---- Create Stripe Customer (idempotent) ----
        customer_id = await self._get_or_create_stripe_customer(actor)

        # ---- Create PaymentIntent ----
        if self._is_stub_key():
            stub_pi_id     = f"pi_stub_{uuid.uuid4().hex[:16]}"
            stub_secret    = f"{stub_pi_id}_secret_stub"
            pi_id          = stub_pi_id
            client_secret  = stub_secret
            pi_status      = "requires_payment_method"
        else:
            stripe.api_key  = settings.STRIPE_SECRET_KEY
            payment_intent  = await asyncio.to_thread(
                stripe.PaymentIntent.create,
                amount=appointment.estimated_price,
                currency=settings.STRIPE_CURRENCY,
                customer=customer_id,
                metadata={
                    "appointment_id": str(appointment.id),
                    "detailer_id":    str(appointment.detailer_id),
                    "service_id":     str(appointment.service_id),
                },
                idempotency_key=f"appt_{appointment.id}",
            )
            pi_id         = payment_intent.id
            client_secret = payment_intent.client_secret
            pi_status     = payment_intent.status

        # ---- Persist PI ID for idempotency ----
        appointment.stripe_payment_intent_id = pi_id
        await self._db.flush()

        await self._audit_repo.log(
            action=AuditAction.PAYMENT_INTENT_CREATED,
            entity_type="appointment",
            entity_id=str(appointment.id),
            actor_id=actor.id,
            metadata={
                "payment_intent_id": pi_id,
                "amount_cents": appointment.estimated_price,
                "currency": settings.STRIPE_CURRENCY,
                "stub": self._is_stub_key(),
            },
        )

        logger.info(
            "PaymentIntent created | appointment=%s pi=%s amount=%d¢ stub=%s",
            appointment_id, pi_id, appointment.estimated_price, self._is_stub_key(),
        )

        return {
            "payment_intent_id": pi_id,
            "client_secret": client_secret,
            "amount_cents": appointment.estimated_price,
            "currency": settings.STRIPE_CURRENCY,
            "status": pi_status,
        }

    # ---------------------------------------------------------------- #
    #  create_refund  (Sprint 4)                                        #
    # ---------------------------------------------------------------- #

    async def create_refund(
        self,
        payment_intent_id: str,
        amount_cents: int,
        reason: str = "requested_by_customer",
    ) -> str | None:
        """
        Issue a (full or partial) Stripe refund against a PaymentIntent.

        Returns the Stripe `re_xxx` refund ID, or None when running with
        a stub key (test / CI environment).

        Called by AppointmentService.transition_status() when a CONFIRMED
        appointment with a captured payment is cancelled.

        Reason values supported by Stripe:
          "duplicate" | "fraudulent" | "requested_by_customer"
        """
        if amount_cents <= 0:
            return None

        if self._is_stub_key() or payment_intent_id.startswith("pi_stub"):
            stub_refund_id = f"re_stub_{uuid.uuid4().hex[:12]}"
            logger.info(
                "Stub refund | pi=%s amount=%d¢ refund_id=%s",
                payment_intent_id, amount_cents, stub_refund_id,
            )
            await self._audit_repo.log(
                action=AuditAction.PAYMENT_REFUNDED,
                entity_type="payment_intent",
                entity_id=payment_intent_id,
                actor_id=None,
                metadata={
                    "refund_id":    stub_refund_id,
                    "amount_cents": amount_cents,
                    "reason":       reason,
                    "stub":         True,
                },
            )
            return stub_refund_id

        stripe.api_key = settings.STRIPE_SECRET_KEY
        refund = await asyncio.to_thread(
            stripe.Refund.create,
            payment_intent=payment_intent_id,
            amount=amount_cents,
            reason=reason,
        )

        await self._audit_repo.log(
            action=AuditAction.PAYMENT_REFUNDED,
            entity_type="payment_intent",
            entity_id=payment_intent_id,
            actor_id=None,
            metadata={
                "refund_id":    refund.id,
                "amount_cents": amount_cents,
                "reason":       reason,
                "stub":         False,
            },
        )

        logger.info(
            "Stripe Refund issued | pi=%s amount=%d¢ refund=%s",
            payment_intent_id, amount_cents, refund.id,
        )
        return refund.id

    # ---------------------------------------------------------------- #
    #  handle_payment_succeeded  (called from Stripe webhook)           #
    # ---------------------------------------------------------------- #

    async def handle_payment_succeeded(self, payment_intent_id: str) -> None:
        """
        Called by the Stripe webhook handler when payment_intent.succeeded fires.

        Logs a PAYMENT_CAPTURED audit event. The appointment status is NOT
        auto-transitioned here because CONFIRMED → IN_PROGRESS is detailer-
        initiated (they start the service). Payment just confirms the booking
        is financially secured.
        """
        stmt = select(Appointment).where(
            Appointment.stripe_payment_intent_id == payment_intent_id,
            Appointment.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        appointment = result.scalar_one_or_none()

        if appointment is None:
            logger.warning(
                "payment_intent.succeeded for unknown PI: %s", payment_intent_id
            )
            return

        await self._audit_repo.log(
            action=AuditAction.PAYMENT_CAPTURED,
            entity_type="appointment",
            entity_id=str(appointment.id),
            actor_id=appointment.client_id,
            metadata={
                "payment_intent_id": payment_intent_id,
                "amount_cents":      appointment.estimated_price,
            },
        )

        logger.info(
            "Payment captured | appointment=%s pi=%s amount=%d¢",
            appointment.id, payment_intent_id, appointment.estimated_price,
        )
