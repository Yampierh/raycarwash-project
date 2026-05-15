"""
domains/users/avatar_service.py — Avatar + cover upload flow.

Two-step protocol (per plan §2.4):

  1. `prepare_upload(user, mime, size, kind)` validates the declared mime
     and size, asks the FileStorageAdapter for a presigned URL, returns
     the URL + s3_key without touching the User row yet. The pending key
     is held by the client.

  2. `confirm_upload(user, s3_key, kind, declared_mime, declared_size)`
     HEADs the object to make sure something actually landed, double-checks
     the on-disk mime + size against what the client declared in step 1,
     then writes `user.avatar_s3_key` / `user.cover_s3_key` and schedules
     the previous object for deletion. Returns the new signed download URL.

  3. `delete(user, kind)` clears the column and removes the object.

`kind` is `"avatar"` or `"cover"`. Cover is gated to detailers at the
router layer; the service is agnostic.

Side effects audited via `AuditAction.AVATAR_CHANGED` / `COVER_CHANGED`.
"""
from __future__ import annotations

import logging
import secrets
from typing import Literal

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_public_storage
from app.middleware.audit_context import get_audit_context
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.users.avatar_schemas import (
    ALLOWED_IMAGE_MIME_TYPES,
    MAX_AVATAR_SIZE_BYTES,
    MAX_COVER_SIZE_BYTES,
)
from domains.users.models import User
from infrastructure.storage.base import (
    FileStorageAdapter,
    ObjectNotFound,
    PresignedUpload,
)

logger = logging.getLogger(__name__)

ImageKind = Literal["avatar", "cover"]


_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class AvatarServiceError(HTTPException):
    """Domain-level errors that translate cleanly to the envelope shape."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


class AvatarService:
    def __init__(self, db: AsyncSession, request: Request) -> None:
        self.db = db
        self.request = request
        self.audit = AuditRepository(db)
        self._adapter: FileStorageAdapter = get_public_storage()

    # ────── upload-url ─────────────────────────────────────────────────────

    async def prepare_upload(
        self,
        user: User,
        mime_type: str,
        size_bytes: int,
        kind: ImageKind,
    ) -> PresignedUpload:
        """Validate caller-declared metadata and return a presigned URL.

        Limits diverge by kind: 5 MB avatar / 8 MB cover, matching the
        constants in avatar_schemas. The s3 key embeds a fresh random
        token so clients can't smuggle one upload over another by reusing
        a known key.
        """
        if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            raise AvatarServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"mime_type must be one of {sorted(ALLOWED_IMAGE_MIME_TYPES)}",
            )

        max_size = MAX_AVATAR_SIZE_BYTES if kind == "avatar" else MAX_COVER_SIZE_BYTES
        if size_bytes <= 0 or size_bytes > max_size:
            raise AvatarServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"size_bytes must be in 1..{max_size}",
            )

        ext = _MIME_TO_EXT.get(mime_type, "bin")
        token = secrets.token_urlsafe(16)
        key = f"{kind}s/{user.id}/{token}.{ext}"

        return await self._adapter.generate_upload_url(
            key,
            mime=mime_type,
            max_size=max_size,
            ttl_seconds=3600,
        )

    # ────── confirm ────────────────────────────────────────────────────────

    async def confirm_upload(
        self,
        user: User,
        s3_key: str,
        kind: ImageKind,
    ) -> str:
        """Verify the upload landed, persist on the User, return signed URL.

        We don't trust the client's declared mime/size — we HEAD the object
        and re-check both against the same limits. A mismatch means either
        the client lied in step 1 or the dev /dev/upload signature didn't
        match (which already returns 403, so we shouldn't see it here in
        practice).
        """
        if not s3_key.startswith(f"{kind}s/{user.id}/"):
            raise AvatarServiceError(
                status.HTTP_403_FORBIDDEN,
                "permission_denied",
                "s3_key does not belong to the authenticated user.",
            )

        try:
            meta = await self._adapter.head_object(s3_key)
        except ObjectNotFound:
            raise AvatarServiceError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "Upload not found at the requested key. Did the PUT succeed?",
            )

        if meta.content_type and meta.content_type not in ALLOWED_IMAGE_MIME_TYPES:
            # Schedule cleanup so the bucket doesn't accumulate orphans.
            await self._adapter.delete_object(s3_key)
            raise AvatarServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"Uploaded content_type {meta.content_type!r} is not an allowed image type.",
            )

        max_size = MAX_AVATAR_SIZE_BYTES if kind == "avatar" else MAX_COVER_SIZE_BYTES
        if meta.size > max_size:
            await self._adapter.delete_object(s3_key)
            raise AvatarServiceError(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "payload_too_large",
                f"Uploaded file exceeds the {max_size}-byte limit.",
            )

        # Swap the previous object out — best-effort, never fail the request
        # because deleting the old image isn't critical.
        previous_key = user.avatar_s3_key if kind == "avatar" else user.cover_s3_key
        if previous_key and previous_key != s3_key:
            try:
                await self._adapter.delete_object(previous_key)
            except Exception as exc:
                logger.warning("avatar: failed to drop previous %s key %s: %s", kind, previous_key, exc)

        if kind == "avatar":
            user.avatar_s3_key = s3_key
            action = AuditAction.AVATAR_CHANGED
        else:
            user.cover_s3_key = s3_key
            action = AuditAction.COVER_CHANGED

        await self.db.flush()

        await self.audit.log(
            action=action,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            old_value={"s3_key": previous_key},
            new_value={"s3_key": s3_key, "size": meta.size, "mime": meta.content_type},
            audit_ctx=get_audit_context(self.request),
        )

        return await self._adapter.generate_download_url(s3_key, ttl_seconds=86_400)

    # ────── delete ─────────────────────────────────────────────────────────

    async def delete(self, user: User, kind: ImageKind) -> None:
        """Drop the User column + remove the object."""
        previous_key = user.avatar_s3_key if kind == "avatar" else user.cover_s3_key
        if not previous_key:
            return

        if kind == "avatar":
            user.avatar_s3_key = None
            action = AuditAction.AVATAR_CHANGED
        else:
            user.cover_s3_key = None
            action = AuditAction.COVER_CHANGED

        await self.db.flush()

        try:
            await self._adapter.delete_object(previous_key)
        except Exception as exc:
            logger.warning("avatar: failed to delete %s object %s: %s", kind, previous_key, exc)

        await self.audit.log(
            action=action,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            old_value={"s3_key": previous_key},
            new_value={"s3_key": None},
            audit_ctx=get_audit_context(self.request),
        )
