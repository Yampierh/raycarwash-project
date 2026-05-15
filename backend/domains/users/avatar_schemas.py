"""
domains/users/avatar_schemas.py — Avatar + cover upload request/response shapes.

The flow has two steps:
  1. POST /users/me/avatar/upload-url
     Body: {mime_type, size_bytes}. Server validates the limits, calls
     FileStorageAdapter.generate_upload_url, returns the URL + s3_key.
  2. Client PUTs the image bytes to that URL (S3 directly in prod,
     /dev/upload via LocalStorageAdapter in dev).
  3. POST /users/me/avatar
     Body: {s3_key}. Server HEADs the object to verify mime + size match
     what was declared in step 1, then sets User.avatar_s3_key.
"""
from __future__ import annotations

from pydantic import Field

from shared.schemas import _BaseRequestSchema, _BaseSchema


# Limits used by both avatar and cover endpoints.
MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_COVER_SIZE_BYTES = 8 * 1024 * 1024   # 8 MB
ALLOWED_IMAGE_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
})


class UploadUrlRequest(_BaseRequestSchema):
    """First step: client declares mime + size before requesting the URL."""
    mime_type: str = Field(..., examples=["image/jpeg"])
    size_bytes: int = Field(..., gt=0, le=MAX_COVER_SIZE_BYTES)


class UploadUrlResponse(_BaseSchema):
    """Server returns everything the client needs to perform the upload.

    `method` reflects the storage adapter: "POST" in dev (LocalStorageAdapter
    posts to /dev/upload), "PUT" in production (S3StorageAdapter generates
    a presigned PUT URL). Clients should use whatever the response says.
    """
    url: str
    method: str
    headers: dict[str, str]
    s3_key: str
    expires_in: int


class ConfirmUploadRequest(_BaseRequestSchema):
    """Second step: client tells the server which key it uploaded to."""
    s3_key: str = Field(..., min_length=1, max_length=512)


class AvatarConfirmResponse(_BaseSchema):
    """What the client gets back after a successful confirm."""
    avatar_url: str | None = None
    cover_url: str | None = None
