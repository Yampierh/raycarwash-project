"""
domains/users/vehicle_photo_router.py — /api/v1/users/me/vehicles/{id}/
photos/* (Phase 4 chunk V).

Endpoints per plan §2.7:
  POST   /me/vehicles/{vehicle_id}/photos/upload-url   presigned PUT (max 4)
  POST   /me/vehicles/{vehicle_id}/photos              confirm uploaded key
  DELETE /me/vehicles/{vehicle_id}/photos/{photo_id}
  GET    /me/vehicles/{vehicle_id}/photos              list

Two-step upload mirrors the avatar flow (avatar_router). No step-up —
vehicle photos are content, not credentials.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from domains.auth.service import get_current_user
from domains.users.models import User
from domains.users.vehicle_photo_schemas import (
    VehiclePhotoConfirmRequest,
    VehiclePhotoResponse,
    VehiclePhotoUploadUrlRequest,
    VehiclePhotoUploadUrlResponse,
)
from domains.users.vehicle_photo_service import (
    get_vehicle_photo_service,
    sign_photo_url,
)
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(
    prefix="/api/v1/users/me/vehicles",
    tags=["User Vehicle Photos"],
)


def _to_response(photo) -> VehiclePhotoResponse:
    return VehiclePhotoResponse(
        id=photo.id,
        vehicle_id=photo.vehicle_id,
        s3_key=photo.s3_key,
        caption=photo.caption,
        sort_order=photo.sort_order,
        photo_url=sign_photo_url(photo.s3_key),
        created_at=photo.created_at,
    )


# ─── List ────────────────────────────────────────────────────────────────────


@router.get(
    "/{vehicle_id}/photos",
    response_model=Envelope[list[VehiclePhotoResponse]],
    summary="List photos for a vehicle the caller owns.",
    responses={404: {"description": "Vehicle not found or not owned."}},
)
async def list_photos(
    request: Request,
    vehicle_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[VehiclePhotoResponse]]:
    service = get_vehicle_photo_service(db, request)
    photos = await service.list_for_vehicle(current_user, vehicle_id)
    return Envelope[list[VehiclePhotoResponse]](
        data=[_to_response(p) for p in photos]
    )


# ─── upload-url ──────────────────────────────────────────────────────────────


@router.post(
    "/{vehicle_id}/photos/upload-url",
    response_model=Envelope[VehiclePhotoUploadUrlResponse],
    summary="Step 1 of vehicle photo upload — returns a presigned URL the "
            "client PUTs the bytes to. Rejects 409 if the vehicle already "
            "holds the per-vehicle photo cap.",
    responses={
        404: {"description": "Vehicle not found or not owned."},
        409: {"description": "Vehicle already at the photo cap."},
        422: {"description": "mime_type or size_bytes outside allowed range."},
    },
)
async def upload_url(
    request: Request,
    body: VehiclePhotoUploadUrlRequest,
    vehicle_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[VehiclePhotoUploadUrlResponse]:
    service = get_vehicle_photo_service(db, request)
    presigned = await service.prepare_upload(
        current_user,
        vehicle_id,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
    )
    return Envelope[VehiclePhotoUploadUrlResponse](
        data=VehiclePhotoUploadUrlResponse(
            url=presigned.url,
            method=presigned.method,
            headers=presigned.headers,
            s3_key=presigned.s3_key,
            expires_in=presigned.expires_in,
        )
    )


# ─── Confirm ─────────────────────────────────────────────────────────────────


@router.post(
    "/{vehicle_id}/photos",
    response_model=Envelope[VehiclePhotoResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Step 2: confirm an upload — HEADs the bytes, then INSERTs the "
            "VehiclePhoto row at the next sort_order slot.",
    responses={
        403: {"description": "s3_key does not belong to this vehicle."},
        404: {"description": "Vehicle or upload not found."},
        409: {"description": "Vehicle filled to the photo cap between prepare and confirm."},
    },
)
async def confirm(
    request: Request,
    body: VehiclePhotoConfirmRequest,
    vehicle_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[VehiclePhotoResponse]:
    service = get_vehicle_photo_service(db, request)
    photo = await service.confirm_upload(
        current_user, vehicle_id, body.s3_key, body.caption,
    )
    await db.commit()
    return Envelope[VehiclePhotoResponse](data=_to_response(photo))


# ─── Delete ──────────────────────────────────────────────────────────────────


@router.delete(
    "/{vehicle_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Hard-delete a vehicle photo + drop the S3 object.",
    responses={404: {"description": "Vehicle or photo not found."}},
)
async def delete_photo(
    request: Request,
    vehicle_id: uuid.UUID = Path(...),
    photo_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = get_vehicle_photo_service(db, request)
    await service.delete(current_user, vehicle_id, photo_id)
    await db.commit()
