"""
domains/users/provider_portfolio_schemas.py — shapes for
`/api/v1/users/me/provider-portfolio` (Phase 5 chunk Y3).

Two-step upload mirrors VehiclePhotos / Avatar. The per-provider cap
of 30 is enforced at both prepare and confirm to close the race
window.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas import _BaseRequestSchema, _BaseSchema


MAX_PORTFOLIO_PHOTO_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB
MAX_PORTFOLIO_PHOTOS_PER_PROVIDER = 30
ALLOWED_PORTFOLIO_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
})


class PortfolioUploadUrlRequest(_BaseRequestSchema):
    mime_type: str = Field(..., examples=["image/jpeg"])
    size_bytes: int = Field(..., gt=0, le=MAX_PORTFOLIO_PHOTO_SIZE_BYTES)


class PortfolioUploadUrlResponse(_BaseSchema):
    url: str
    method: str
    headers: dict[str, str]
    s3_key: str
    expires_in: int


class PortfolioConfirmRequest(_BaseRequestSchema):
    s3_key: str = Field(..., min_length=1, max_length=255)
    caption: str | None = Field(default=None, max_length=200)
    # Free-form: "before", "after", "hero", or anything detailers want
    # to group by. Backend doesn't constrain — frontend renders unknown
    # tags as plain text.
    tag: str | None = Field(default=None, max_length=40)


class PortfolioPhotoResponse(_BaseSchema):
    id: uuid.UUID
    provider_user_id: uuid.UUID
    s3_key: str
    caption: str | None = None
    tag: str | None = None
    sort_order: int
    photo_url: str | None = None
    created_at: datetime
