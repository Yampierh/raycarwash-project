"""
domains/users/address_router.py — /api/v1/users/me/addresses (Phase 4 chunk T).

Endpoints per plan §2.9:
  GET    /me/addresses             list active addresses
  POST   /me/addresses             create + geocode (any-auth)
  GET    /me/addresses/{id}        detail
  PATCH  /me/addresses/{id}        partial update (re-geocodes only on
                                   address-line / city / state / zip / country)
  DELETE /me/addresses/{id}        soft-delete + auto-promote replacement
  PATCH  /me/addresses/{id}/default  atomic pivot of the default flag

Step-up is NOT required — addresses are non-financial data the user
edits during onboarding and the booking flow. Audit log captures every
write via the AuditContext middleware.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from domains.auth.service import get_current_user
from domains.users.address_schemas import (
    AddressCreateRequest,
    AddressResponse,
    AddressUpdateRequest,
)
from domains.users.address_service import get_address_service
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(prefix="/api/v1/users/me/addresses", tags=["User Addresses"])


# ─── List ────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=Envelope[list[AddressResponse]],
    summary="List the user's active addresses (newest first).",
)
async def list_addresses(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[AddressResponse]]:
    service = get_address_service(db, request)
    rows = await service.list_for_user(current_user)
    return Envelope[list[AddressResponse]](
        data=[AddressResponse.model_validate(r) for r in rows],
    )


# ─── Detail ──────────────────────────────────────────────────────────────────


@router.get(
    "/{address_id}",
    response_model=Envelope[AddressResponse],
    summary="Fetch one of the user's addresses.",
    responses={404: {"description": "Address not found or not owned by the caller."}},
)
async def get_address(
    request: Request,
    address_id: uuid.UUID = Path(..., description="UserAddress UUID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[AddressResponse]:
    service = get_address_service(db, request)
    row = await service.get_or_404(current_user, address_id)
    return Envelope[AddressResponse](data=AddressResponse.model_validate(row))


# ─── Create ──────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=Envelope[AddressResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create an address. Geocodes synchronously; persists with NULL "
            "coordinates if the geocoding provider is unavailable.",
)
async def create_address(
    request: Request,
    body: AddressCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[AddressResponse]:
    service = get_address_service(db, request)
    row = await service.create(current_user, body)
    await db.commit()
    return Envelope[AddressResponse](data=AddressResponse.model_validate(row))


# ─── Update ──────────────────────────────────────────────────────────────────


@router.patch(
    "/{address_id}",
    response_model=Envelope[AddressResponse],
    summary="Partial update. Re-geocodes only when address-line, city, "
            "state, zip or country change.",
    responses={404: {"description": "Address not found or not owned by the caller."}},
)
async def update_address(
    request: Request,
    body: AddressUpdateRequest,
    address_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[AddressResponse]:
    service = get_address_service(db, request)
    row = await service.update(current_user, address_id, body)
    await db.commit()
    return Envelope[AddressResponse](data=AddressResponse.model_validate(row))


# ─── Set default ─────────────────────────────────────────────────────────────


@router.patch(
    "/{address_id}/default",
    response_model=Envelope[AddressResponse],
    summary="Atomically promote this address to default. One UPDATE clears "
            "the previous default and sets the new one — no transient state "
            "violates the partial unique index.",
    responses={404: {"description": "Address not found or not owned by the caller."}},
)
async def set_default(
    request: Request,
    address_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[AddressResponse]:
    service = get_address_service(db, request)
    row = await service.set_default(current_user, address_id)
    await db.commit()
    return Envelope[AddressResponse](data=AddressResponse.model_validate(row))


# ─── Delete ──────────────────────────────────────────────────────────────────


@router.delete(
    "/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Soft-delete. If the address was the default, the oldest "
            "remaining active address is promoted automatically.",
    responses={404: {"description": "Address not found or not owned by the caller."}},
)
async def delete_address(
    request: Request,
    address_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = get_address_service(db, request)
    await service.delete(current_user, address_id)
    await db.commit()
