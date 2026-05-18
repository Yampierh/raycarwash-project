"""
domains/users/provider_documents_schemas.py — shapes for
`/api/v1/users/me/provider-documents` (Phase 5 chunk Y4).

KYC artifacts (insurance, business license, certifications, W-9).
Files live in the PRIVATE bucket — download URLs are short-TTL
presigned (1 h) so they can't be reused if leaked.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import Field

from shared.schemas import _BaseRequestSchema, _BaseSchema


MAX_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB — PDFs can be big
ALLOWED_DOCUMENT_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "application/pdf",
})

# Conventional document type strings — kept in sync with DocumentType
# enum in domains/users/document.py. Stored as plain String so adding
# a new category doesn't need a migration.
VALID_DOCUMENT_TYPES = frozenset({
    "insurance",
    "business_license",
    "certification",
    "w9",
    "other",
})


class DocumentUploadUrlRequest(_BaseRequestSchema):
    type: str = Field(..., examples=["insurance"])
    mime_type: str = Field(..., examples=["application/pdf"])
    size_bytes: int = Field(..., gt=0, le=MAX_DOCUMENT_SIZE_BYTES)


class DocumentUploadUrlResponse(_BaseSchema):
    url: str
    method: str
    headers: dict[str, str]
    s3_key: str
    expires_in: int


class DocumentConfirmRequest(_BaseRequestSchema):
    s3_key: str = Field(..., min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=120)
    type: str = Field(..., examples=["insurance"])
    expires_at: date | None = None


class DocumentResponse(_BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    expires_at: date | None = None
    # Short-TTL presigned download URL (1 h). The frontend re-fetches
    # the list when the user opens the screen so this URL is never
    # cached client-side past its TTL window.
    download_url: str | None = None
    created_at: datetime
    updated_at: datetime
