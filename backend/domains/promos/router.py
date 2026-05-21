"""
domains/promos/router.py — public endpoints for promo lookup + preview.

Auth is optional: when present, the response includes per-user
eligibility (`eligible`, `remaining_per_user`); when anonymous, only
global eligibility is computed.

These endpoints live under /api/v1/promo/* which is post-Phase-0, so we
use EnvelopeRouter for the Envelope[T] response shape (ADR-001).
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from domains.auth.service import AuthService
from domains.promos.schemas import (
    PromoCodeRead, PromoPreviewRequest, PromoPreviewResponse,
)
from domains.promos.service import PromoService
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope


router = EnvelopeRouter(prefix="/api/v1/promo", tags=["Promo"])


async def _maybe_user(
    db: AsyncSession,
    authorization: str | None,
) -> User | None:
    """Decode the Bearer token if present + valid. Returns None for any
    failure (missing, malformed, expired) — promo lookup remains usable
    anonymously."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    try:
        payload = AuthService.decode_token(token, expected_type="access")
    except Exception:
        return None
    user_id_raw = payload.get("sub")
    if not user_id_raw:
        return None
    try:
        uid = uuid.UUID(user_id_raw)
    except ValueError:
        return None
    user = (await db.execute(
        select(User).where(User.id == uid, User.is_deleted.is_(False))
    )).scalar_one_or_none()
    return user


@router.get(
    "/{code}",
    response_model=Envelope[PromoCodeRead],
    summary="Look up a promo code (auth optional — adds per-user eligibility)",
)
async def get_promo(
    code: str,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Envelope[PromoCodeRead]:
    current_user = await _maybe_user(db, authorization)
    user_id = current_user.id if current_user else None
    promo, reason, remaining = await PromoService(db).lookup(code, user_id=user_id)
    if promo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Promo not found.")

    eligible = reason is None
    payload = PromoCodeRead(
        id=promo.id,
        code=promo.code,
        description=promo.description,
        discount_type=promo.discount_type,  # type: ignore[arg-type]
        discount_amount=promo.discount_amount,
        min_order_cents=promo.min_order_cents,
        valid_from=promo.valid_from,
        valid_until=promo.valid_until,
        is_active=promo.is_active,
        eligible=eligible if user_id else None,
        ineligible_reason=reason,
        remaining_per_user=remaining,
    )
    return Envelope[PromoCodeRead](data=payload)


@router.post(
    "/preview",
    response_model=Envelope[PromoPreviewResponse],
    summary="Preview the discount a promo code would yield against a subtotal",
)
async def preview_promo(
    body: PromoPreviewRequest,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Envelope[PromoPreviewResponse]:
    current_user = await _maybe_user(db, authorization)
    user_id = current_user.id if current_user else None
    eligible, discount, final, reason = await PromoService(db).preview(
        code=body.code,
        subtotal_cents=body.subtotal_cents,
        user_id=user_id,
    )
    payload = PromoPreviewResponse(
        code=body.code.strip().upper(),
        eligible=eligible,
        discount_cents=discount,
        final_cents=final,
        reason=reason,
    )
    return Envelope[PromoPreviewResponse](data=payload)
