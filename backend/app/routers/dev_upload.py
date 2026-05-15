"""
app/routers/dev_upload.py — Development-only file upload sink.

Receives the binary body posted by LocalStorageAdapter's presigned-equivalent
URL. The frontend never sees this — it just POSTs to the URL returned by
`generate_upload_url`. In production, AWS S3 receives the upload directly and
this router is not registered.

Routes are gated by `RAYCARWASH_ENV != "production"` at registration time
(see api/router.py).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.config import get_settings
from infrastructure.storage.local import LocalStorageAdapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dev", tags=["Development"])


@router.post(
    "/upload",
    summary="Receive a local-storage upload (dev only — never registered in prod).",
)
async def dev_upload(
    request: Request,
    bucket: str = Query(..., min_length=1, max_length=64),
    key: str = Query(..., min_length=1, max_length=512),
    mime: str = Query(..., min_length=1, max_length=128),
    max_size: int = Query(..., ge=1, le=200 * 1024 * 1024),
    sig: str = Query(..., min_length=8, max_length=128),
) -> dict:
    """
    Validates the HMAC signature, enforces the size cap, and writes the body to
    disk under STORAGE_LOCAL_PATH/{bucket}/{key}. Returns the bytes written.
    """
    settings = get_settings()
    if settings.RAYCARWASH_ENV == "production":
        # Belt-and-suspenders: even if api/router.py forgot to gate, refuse here.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="not_found",
        )

    adapter = LocalStorageAdapter(bucket=bucket)
    if not adapter.verify_signature(key, mime, max_size, sig):
        logger.warning("dev_upload: bad signature for key=%s bucket=%s", key, bucket)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid_signature",
        )

    body = await request.body()
    if len(body) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="payload_too_large",
        )

    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip()
    if content_type and content_type != mime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="mime_mismatch",
        )

    bytes_written = adapter.write_bytes(key, body)
    logger.info("dev_upload OK | bucket=%s key=%s bytes=%d", bucket, key, bytes_written)
    return {"bucket": bucket, "key": key, "size": bytes_written}
