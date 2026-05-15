"""
domains/users/contact_change_router.py — /users/me/email/* and /phone/*.

  POST /users/me/email/change-request   step-up, returns 202 ack
  POST /users/me/email/change-confirm   public, consumes token
  POST /users/me/phone/change-request   step-up, returns 202 ack
  POST /users/me/phone/change-verify    auth + OTP

Step-up is enforced via the Phase 0 dependency. The change-confirm
endpoint is intentionally PUBLIC (the user might be on a different
device than the one that initiated the request); idempotency is provided
by the one-shot token + consumed_at column.
"""
from __future__ import annotations

from fastapi import Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.core.step_up import require_step_up
from domains.auth.service import get_current_user
from domains.users.contact_change_schemas import (
    ContactChangeAck,
    ContactChangeSuccess,
    EmailChangeConfirm,
    EmailChangeRequest,
    PhoneChangeRequest,
    PhoneChangeVerify,
)
from domains.users.contact_change_service import (
    ContactChangeService,
    _mask_email,
    _mask_phone,
)
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(prefix="/api/v1/users/me", tags=["Users · Contact"])


# ─── /email/* ────────────────────────────────────────────────────────────────


@router.post(
    "/email/change-request",
    response_model=Envelope[ContactChangeAck],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate an email change. Always returns 202 (anti-enumeration).",
)
async def email_change_request(
    body: EmailChangeRequest,
    request: Request,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ContactChangeAck]:
    request.state.user = current_user
    service = ContactChangeService(db, request)
    dev_token = await service.request_email_change(
        current_user, str(body.new_email), body.current_password,
    )
    return Envelope(data=ContactChangeAck(dev_token=dev_token))


@router.post(
    "/email/change-confirm",
    response_model=Envelope[ContactChangeSuccess],
    summary="Consume the link emailed to the new address. Public — no token required.",
)
async def email_change_confirm(
    body: EmailChangeConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Envelope[ContactChangeSuccess]:
    service = ContactChangeService(db, request)
    user, new_email = await service.confirm_email_change(body.token)
    return Envelope(data=ContactChangeSuccess(
        new_value_masked=_mask_email(new_email),
        sessions_invalidated=True,
    ))


# ─── /phone/* ────────────────────────────────────────────────────────────────


@router.post(
    "/phone/change-request",
    response_model=Envelope[ContactChangeAck],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate a phone change. Always returns 202 (anti-enumeration).",
)
async def phone_change_request(
    body: PhoneChangeRequest,
    request: Request,
    current_user: User = Depends(require_step_up),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ContactChangeAck]:
    request.state.user = current_user
    service = ContactChangeService(db, request)
    dev_token = await service.request_phone_change(
        current_user, body.new_phone, body.current_password,
    )
    return Envelope(data=ContactChangeAck(dev_token=dev_token))


@router.post(
    "/phone/change-verify",
    response_model=Envelope[ContactChangeSuccess],
    summary="Verify the SMS OTP and swap the user's phone number.",
)
async def phone_change_verify(
    body: PhoneChangeVerify,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ContactChangeSuccess]:
    request.state.user = current_user
    service = ContactChangeService(db, request)
    user, new_phone = await service.verify_phone_change(current_user, body.otp)
    return Envelope(data=ContactChangeSuccess(
        new_value_masked=_mask_phone(new_phone),
        sessions_invalidated=True,
    ))
