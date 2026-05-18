"""
domains/users/vehicle_photo_service.py — manages VehiclePhoto rows
(Phase 4 chunk V).

Mirrors AvatarService two-step protocol:
  1. prepare_upload(vehicle, mime, size) → presigned URL keyed under
     vehicle_photos/{vehicle_id}/{token}.{ext}.
  2. confirm_upload(vehicle, s3_key, caption) → HEAD verifies the bytes
     landed, then INSERTs a VehiclePhoto row at the next sort_order.

Enforces per-vehicle cap of MAX_PHOTOS_PER_VEHICLE (4) at the service
layer — there's no schema-level constraint, and shouldn't be: a
photo limit is a product decision that changes more often than a
schema migration.

Ownership: every operation goes through _get_owned_vehicle which
404s if the caller doesn't own the vehicle. This matters because the
Profile Hub later joins photos in by vehicle_id, and we never want
a cross-user disclosure.
"""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_public_storage
from app.middleware.audit_context import AuditContext, get_audit_context
from domains.audit.repository import AuditRepository
from domains.users.vehicle_photo_schemas import (
    ALLOWED_PHOTO_MIME_TYPES,
    MAX_PHOTOS_PER_VEHICLE,
    MAX_VEHICLE_PHOTO_SIZE_BYTES,
)
from domains.users.models import User
from domains.vehicles.models import Vehicle
from domains.vehicles.vehicle_photo import VehiclePhoto
from infrastructure.storage.base import (
    FileStorageAdapter,
    ObjectNotFound,
    PresignedUpload,
)

logger = logging.getLogger(__name__)


_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class VehiclePhotoServiceError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


class VehiclePhotoService:
    def __init__(self, db: AsyncSession, audit_ctx: AuditContext) -> None:
        self.db = db
        self.audit_ctx = audit_ctx
        self.audit_repo = AuditRepository(db)
        self._adapter: FileStorageAdapter = get_public_storage()

    # ─── Common: ownership + lookup helpers ────────────────────────────────

    async def _get_owned_vehicle(
        self, user: User, vehicle_id: uuid.UUID
    ) -> Vehicle:
        row = (await self.db.execute(
            select(Vehicle)
            .where(
                Vehicle.id == vehicle_id,
                Vehicle.owner_id == user.id,
                Vehicle.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if row is None:
            raise VehiclePhotoServiceError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "Vehicle not found.",
            )
        return row

    async def list_for_vehicle(
        self, user: User, vehicle_id: uuid.UUID
    ) -> list[VehiclePhoto]:
        await self._get_owned_vehicle(user, vehicle_id)
        rows = (await self.db.scalars(
            select(VehiclePhoto)
            .where(VehiclePhoto.vehicle_id == vehicle_id)
            .order_by(VehiclePhoto.sort_order.asc(), VehiclePhoto.created_at.asc())
        )).all()
        return list(rows)

    # ─── upload-url ─────────────────────────────────────────────────────────

    async def prepare_upload(
        self,
        user: User,
        vehicle_id: uuid.UUID,
        mime_type: str,
        size_bytes: int,
    ) -> PresignedUpload:
        vehicle = await self._get_owned_vehicle(user, vehicle_id)

        if mime_type not in ALLOWED_PHOTO_MIME_TYPES:
            raise VehiclePhotoServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"mime_type must be one of {sorted(ALLOWED_PHOTO_MIME_TYPES)}",
            )
        if size_bytes <= 0 or size_bytes > MAX_VEHICLE_PHOTO_SIZE_BYTES:
            raise VehiclePhotoServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"size_bytes must be in 1..{MAX_VEHICLE_PHOTO_SIZE_BYTES}",
            )

        # Photo cap enforced at request time — also re-enforced at
        # confirm_upload to handle the (rare) double-upload race.
        photo_count = await self.db.scalar(
            select(func.count())
            .select_from(VehiclePhoto)
            .where(VehiclePhoto.vehicle_id == vehicle.id)
        ) or 0
        if photo_count >= MAX_PHOTOS_PER_VEHICLE:
            raise VehiclePhotoServiceError(
                status.HTTP_409_CONFLICT,
                "conflict",
                f"Vehicle already has the maximum of {MAX_PHOTOS_PER_VEHICLE} photos.",
            )

        ext = _MIME_TO_EXT.get(mime_type, "bin")
        token = secrets.token_urlsafe(16)
        key = f"vehicle_photos/{vehicle.id}/{token}.{ext}"

        return await self._adapter.generate_upload_url(
            key,
            mime=mime_type,
            max_size=MAX_VEHICLE_PHOTO_SIZE_BYTES,
            ttl_seconds=3600,
        )

    # ─── confirm ────────────────────────────────────────────────────────────

    async def confirm_upload(
        self,
        user: User,
        vehicle_id: uuid.UUID,
        s3_key: str,
        caption: str | None,
    ) -> VehiclePhoto:
        vehicle = await self._get_owned_vehicle(user, vehicle_id)

        # Same path-prefix anti-spoof check we use for avatars: the key
        # must start with vehicle_photos/{vehicle_id}/. Without this a
        # client could confirm an arbitrary key in the public bucket
        # and bind it to their vehicle.
        if not s3_key.startswith(f"vehicle_photos/{vehicle.id}/"):
            raise VehiclePhotoServiceError(
                status.HTTP_403_FORBIDDEN,
                "permission_denied",
                "s3_key does not belong to this vehicle.",
            )

        try:
            meta = await self._adapter.head_object(s3_key)
        except ObjectNotFound:
            raise VehiclePhotoServiceError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "Upload not found at the requested key. Did the PUT succeed?",
            )

        if meta.content_type and meta.content_type not in ALLOWED_PHOTO_MIME_TYPES:
            await self._adapter.delete_object(s3_key)
            raise VehiclePhotoServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"Uploaded content_type {meta.content_type!r} is not an allowed image type.",
            )

        if meta.size > MAX_VEHICLE_PHOTO_SIZE_BYTES:
            await self._adapter.delete_object(s3_key)
            raise VehiclePhotoServiceError(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "payload_too_large",
                f"Uploaded file exceeds the {MAX_VEHICLE_PHOTO_SIZE_BYTES}-byte limit.",
            )

        # Recheck the cap — a concurrent upload could have hit between
        # prepare_upload and confirm_upload. Drop the just-uploaded
        # bytes if so.
        photo_count = await self.db.scalar(
            select(func.count())
            .select_from(VehiclePhoto)
            .where(VehiclePhoto.vehicle_id == vehicle.id)
        ) or 0
        if photo_count >= MAX_PHOTOS_PER_VEHICLE:
            await self._adapter.delete_object(s3_key)
            raise VehiclePhotoServiceError(
                status.HTTP_409_CONFLICT,
                "conflict",
                f"Vehicle already has the maximum of {MAX_PHOTOS_PER_VEHICLE} photos.",
            )

        row = VehiclePhoto(
            vehicle_id=vehicle.id,
            s3_key=s3_key,
            caption=caption,
            sort_order=int(photo_count),  # next slot
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    # ─── delete ─────────────────────────────────────────────────────────────

    async def delete(
        self,
        user: User,
        vehicle_id: uuid.UUID,
        photo_id: uuid.UUID,
    ) -> None:
        vehicle = await self._get_owned_vehicle(user, vehicle_id)

        row = (await self.db.execute(
            select(VehiclePhoto)
            .where(
                VehiclePhoto.id == photo_id,
                VehiclePhoto.vehicle_id == vehicle.id,
            )
        )).scalar_one_or_none()
        if row is None:
            raise VehiclePhotoServiceError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "Vehicle photo not found.",
            )

        s3_key = row.s3_key
        await self.db.delete(row)
        await self.db.flush()

        # Best-effort cleanup of the object — the row is gone either way.
        try:
            await self._adapter.delete_object(s3_key)
        except Exception as exc:
            logger.warning("vehicle_photo: drop %s failed: %s", s3_key, exc)


def get_vehicle_photo_service(db: AsyncSession, request) -> VehiclePhotoService:
    return VehiclePhotoService(db=db, audit_ctx=get_audit_context(request))


def sign_photo_url(s3_key: str | None) -> str | None:
    """Build a download URL for a vehicle photo s3 key. Used by the
    router AND by the Profile Hub vehicles block, so the URL format
    stays consistent."""
    if not s3_key:
        return None
    try:
        adapter = get_public_storage()
        return f"/storage/{adapter.bucket}/{s3_key}"
    except Exception as exc:
        logger.warning("vehicle_photo: failed to sign URL for %s: %s", s3_key, exc)
        return None
