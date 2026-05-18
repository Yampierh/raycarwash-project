"""
domains/users/payment_method_router.py — /api/v1/users/me/payment-methods
(Phase 4 chunk U).

Endpoints per plan §2.8:
  GET    /me/payment-methods              list active
  POST   /me/payment-methods/setup-intent step-up; returns client_secret
  GET    /me/payment-methods/{id}         detail
  PATCH  /me/payment-methods/{id}/default atomic default pivot
  DELETE /me/payment-methods/{id}         step-up; soft-delete + Stripe detach

Step-up guards the two routes that move money: creating an Intent (which
authorizes Stripe to bill the saved card later) and deleting a card
(rate-limit on enumeration + protects against session takeover wiping
billing). List / detail / set-default don't need step-up — they are
read-mostly UX.

Idempotency: the SetupIntent endpoint forwards Idempotency-Key to Stripe
(adapter signature carries it). Hotfix H2 already binds the cache key to
the request body hash, so a retry with the same payload returns the
cached client_secret rather than minting a new SetupIntent.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Header, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.core.step_up import require_step_up
from domains.auth.service import get_current_user
from domains.users.models import User
from domains.users.payment_method_schemas import (
    PaymentMethodResponse,
    SetupIntentRequest,
    SetupIntentResponse,
)
from domains.users.payment_method_service import (
    get_payment_method_service,
    get_publishable_key,
)
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(
    prefix="/api/v1/users/me/payment-methods",
    tags=["User Payment Methods"],
)


# ─── List ────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=Envelope[list[PaymentMethodResponse]],
    summary="List the user's active payment methods.",
)
async def list_payment_methods(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[PaymentMethodResponse]]:
    service = get_payment_method_service(db, request)
    rows = await service.list_for_user(current_user)
    return Envelope[list[PaymentMethodResponse]](
        data=[PaymentMethodResponse.model_validate(r) for r in rows],
    )


# ─── Setup intent ────────────────────────────────────────────────────────────


@router.post(
    "/setup-intent",
    response_model=Envelope[SetupIntentResponse],
    summary="Mint a Stripe SetupIntent so the SDK can attach a new card. "
            "Returns client_secret + publishable key.",
    responses={
        401: {"description": "Step-up auth required (no recent re-auth)."},
        502: {"description": "Stripe is currently unavailable."},
    },
)
async def create_setup_intent(
    request: Request,
    _body: SetupIntentRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> Envelope[SetupIntentResponse]:
    service = get_payment_method_service(db, request)
    intent = await service.create_setup_intent(
        current_user, idempotency_key=idempotency_key,
    )
    # Nothing to commit — SetupIntent lives at Stripe; local rows are
    # written by the payment_method.attached webhook handler.
    return Envelope[SetupIntentResponse](
        data=SetupIntentResponse(
            setup_intent_id=intent.setup_intent_id,
            client_secret=intent.client_secret,
            publishable_key=get_publishable_key(),
        )
    )


# ─── Detail ──────────────────────────────────────────────────────────────────


@router.get(
    "/{pm_id}",
    response_model=Envelope[PaymentMethodResponse],
    summary="Fetch one of the user's payment methods.",
    responses={404: {"description": "Payment method not found or not owned."}},
)
async def get_payment_method(
    request: Request,
    pm_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[PaymentMethodResponse]:
    service = get_payment_method_service(db, request)
    row = await service.get_or_404(current_user, pm_id)
    return Envelope[PaymentMethodResponse](
        data=PaymentMethodResponse.model_validate(row)
    )


# ─── Set default ─────────────────────────────────────────────────────────────


@router.patch(
    "/{pm_id}/default",
    response_model=Envelope[PaymentMethodResponse],
    summary="Atomically promote this payment method to default.",
    responses={404: {"description": "Payment method not found or not owned."}},
)
async def set_default(
    request: Request,
    pm_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[PaymentMethodResponse]:
    service = get_payment_method_service(db, request)
    row = await service.set_default(current_user, pm_id)
    await db.commit()
    return Envelope[PaymentMethodResponse](
        data=PaymentMethodResponse.model_validate(row)
    )


# ─── Delete ──────────────────────────────────────────────────────────────────


@router.delete(
    "/{pm_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Detach a payment method. Soft-deletes locally and detaches at "
            "Stripe. If Stripe detach fails the local row stays removed and "
            "a webhook reconciliation worker will retry — the user-facing "
            "list is always correct.",
    responses={
        401: {"description": "Step-up auth required (no recent re-auth)."},
        404: {"description": "Payment method not found or not owned."},
    },
)
async def delete_payment_method(
    request: Request,
    pm_id: uuid.UUID = Path(...),
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = get_payment_method_service(db, request)
    await service.delete(current_user, pm_id)
    await db.commit()
