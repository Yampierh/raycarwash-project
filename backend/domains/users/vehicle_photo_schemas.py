"""
domains/users/vehicle_photo_schemas.py — shapes for
`/api/v1/users/me/vehicles/{id}/photos/*` (Phase 4 chunk V).

Mirrors avatar_schemas: two-step upload-url → confirm flow, with
per-vehicle photo cap enforced at the service layer (max 4 per
plan §2.7).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas import _BaseRequestSchema, _BaseSchema


MAX_VEHICLE_PHOTO_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB — same envelope as cover
MAX_PHOTOS_PER_VEHICLE = 4
ALLOWED_PHOTO_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
})


class VehiclePhotoUploadUrlRequest(_BaseRequestSchema):
    mime_type: str = Field(..., examples=["image/jpeg"])
    size_bytes: int = Field(..., gt=0, le=MAX_VEHICLE_PHOTO_SIZE_BYTES)


class VehiclePhotoUploadUrlResponse(_BaseSchema):
    url: str
    method: str
    headers: dict[str, str]
    s3_key: str
    expires_in: int


class VehiclePhotoConfirmRequest(_BaseRequestSchema):
    s3_key: str = Field(..., min_length=1, max_length=255)
    caption: str | None = Field(default=None, max_length=120)


class VehiclePhotoResponse(_BaseSchema):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    s3_key: str
    caption: str | None = None
    sort_order: int
    photo_url: str | None = None
    created_at: datetime
