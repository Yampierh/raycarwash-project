# app/routers/payment_router.py

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.users.models import User
from domains.payments.schemas import PaymentIntentRequest, PaymentIntentResponse
from domains.auth.service import get_current_user
from domains.payments.service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.post(
    "/create-intent",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Stripe PaymentIntent for a confirmed appointment.",
    responses={
        402: {"description": "Payment cannot be initiated for this appointment."},
        404: {"description": "Appointment not found."},
    },
)
async def create_payment_intent(
    payload: PaymentIntentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PaymentIntentResponse:
    """
    Creates (or retrieves) a Stripe PaymentIntent for the appointment.

    Returns a `client_secret` which the React Native frontend passes
    directly to the Stripe SDK (`stripe.confirmPayment(client_secret)`).
    This keeps card data off our servers entirely (PCI SAQ A compliance).

    Idempotent: calling this endpoint twice for the same appointment
    returns the same PaymentIntent.
    """
    payment_svc = PaymentService(db)
    result = await payment_svc.create_payment_intent(
        appointment_id=payload.appointment_id,
        actor=current_user,
    )
    return PaymentIntentResponse(**result)