"""
domains/users/client_preferences_router.py — /api/v1/users/me/
client-preferences (Phase 4 chunk V).

Two endpoints (plan §2.11):
  GET /me/client-preferences   read default_vehicle_id, default_address_id,
                                marketing_opt_in, frequency_preference
  PUT /me/client-preferences   replace (matches the schema's semantics —
                                a PUT writes the entire preferences object)

These four fields live on ClientProfile. Validation:
  - default_vehicle_id must refer to a vehicle owned by the caller (or
    null to clear).
  - default_address_id must refer to a UserAddress owned by the caller
    (or null to clear).
  - frequency_preference is a free-form string today (max 20 chars by
    the column); the plan §5 calls out "weekly" / "monthly" as the two
    intended values but we don't enum-constrain so future cadences
    don't need a migration.

Audit logged via PROFILE_UPDATED with old_value/new_value so the
profile-changes history endpoint (Phase 8) can render diffs.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.middleware.audit_context import get_audit_context
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.service import get_current_user
from domains.users.models import ClientProfile, User
from domains.users.user_address import UserAddress
from domains.vehicles.models import Vehicle
from infrastructure.db.session import get_db
from shared.schemas import Envelope, _BaseRequestSchema, _BaseSchema

router = EnvelopeRouter(
    prefix="/api/v1/users/me/client-preferences",
    tags=["User Client Preferences"],
)


class ClientPreferencesResponse(_BaseSchema):
    default_vehicle_id: uuid.UUID | None = None
    default_address_id: uuid.UUID | None = None
    marketing_opt_in: bool = False
    frequency_preference: str | None = None


class ClientPreferencesRequest(_BaseRequestSchema):
    default_vehicle_id: uuid.UUID | None = None
    default_address_id: uuid.UUID | None = None
    marketing_opt_in: bool = False
    frequency_preference: str | None = Field(default=None, max_length=20)


async def _get_or_create_client_profile(
    db: AsyncSession, user: User
) -> ClientProfile:
    """Ensure the caller has a ClientProfile row. Legacy users created
    before Phase 1 lacked one — write a fresh row on first touch rather
    than 404'ing them."""
    cp = (await db.execute(
        select(ClientProfile).where(ClientProfile.user_id == user.id)
    )).scalar_one_or_none()
    if cp is None:
        cp = ClientProfile(user_id=user.id)
        db.add(cp)
        await db.flush()
    return cp


@router.get(
    "",
    response_model=Envelope[ClientPreferencesResponse],
    summary="Read the caller's client preferences (defaults + marketing).",
)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ClientPreferencesResponse]:
    cp = await _get_or_create_client_profile(db, current_user)
    return Envelope[ClientPreferencesResponse](
        data=ClientPreferencesResponse(
            default_vehicle_id=cp.default_vehicle_id,
            default_address_id=cp.default_address_id,
            marketing_opt_in=cp.marketing_email_opt_in,
            frequency_preference=cp.frequency_preference,
        )
    )


@router.put(
    "",
    response_model=Envelope[ClientPreferencesResponse],
    summary="Replace the caller's client preferences. Validates that "
            "default_vehicle_id and default_address_id refer to resources "
            "owned by the caller (or NULL to clear).",
    responses={
        404: {"description": "Referenced vehicle or address does not belong to caller."},
    },
)
async def put_preferences(
    request: Request,
    body: ClientPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ClientPreferencesResponse]:
    cp = await _get_or_create_client_profile(db, current_user)

    # Validate FK targets BEFORE we mutate so a half-applied PUT can't
    # leave the row pointing at someone else's resource.
    if body.default_vehicle_id is not None:
        owned = await db.scalar(
            select(Vehicle.id).where(
                Vehicle.id == body.default_vehicle_id,
                Vehicle.owner_id == current_user.id,
                Vehicle.is_deleted.is_(False),
            )
        )
        if owned is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "resource_not_found",
                    "message": "default_vehicle_id does not refer to one of your vehicles.",
                },
            )

    if body.default_address_id is not None:
        owned = await db.scalar(
            select(UserAddress.id).where(
                UserAddress.id == body.default_address_id,
                UserAddress.user_id == current_user.id,
                UserAddress.is_deleted.is_(False),
            )
        )
        if owned is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "resource_not_found",
                    "message": "default_address_id does not refer to one of your addresses.",
                },
            )

    old_snapshot = {
        "default_vehicle_id": str(cp.default_vehicle_id) if cp.default_vehicle_id else None,
        "default_address_id": str(cp.default_address_id) if cp.default_address_id else None,
        "marketing_opt_in": cp.marketing_email_opt_in,
        "frequency_preference": cp.frequency_preference,
    }
    cp.default_vehicle_id = body.default_vehicle_id
    cp.default_address_id = body.default_address_id
    cp.marketing_email_opt_in = body.marketing_opt_in
    cp.frequency_preference = body.frequency_preference
    await db.flush()

    new_snapshot = {
        "default_vehicle_id": str(cp.default_vehicle_id) if cp.default_vehicle_id else None,
        "default_address_id": str(cp.default_address_id) if cp.default_address_id else None,
        "marketing_opt_in": cp.marketing_email_opt_in,
        "frequency_preference": cp.frequency_preference,
    }

    await AuditRepository(db).log(
        action=AuditAction.PROFILE_UPDATED,
        entity_type="client_profile",
        entity_id=str(cp.id),
        actor_id=current_user.id,
        old_value=old_snapshot,
        new_value=new_snapshot,
        audit_ctx=get_audit_context(request),
    )
    await db.commit()

    return Envelope[ClientPreferencesResponse](
        data=ClientPreferencesResponse(
            default_vehicle_id=cp.default_vehicle_id,
            default_address_id=cp.default_address_id,
            marketing_opt_in=cp.marketing_email_opt_in,
            frequency_preference=cp.frequency_preference,
        )
    )
