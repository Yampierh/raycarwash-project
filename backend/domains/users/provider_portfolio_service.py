"""
domains/users/provider_portfolio_service.py — orchestration for
`/api/v1/users/me/provider-portfolio*` (Phase 5 chunk Y3).

Two-step upload pattern mirrors VehiclePhotoService (Phase 4 chunk V):
prepare → presigned URL → client PUTs bytes → confirm.

Per-provider photo cap (30) enforced at BOTH prepare_upload and
confirm_upload — closes the race window where two concurrent uploads
at count=29 could both succeed.

Requires the caller to have an activated ProviderProfile. Photos live
in the public bucket because they're shown on the public detailer
search results / profile page (so non-authenticated clients can
preview work before tapping into the booking flow).

Ownership anti-spoof: the s3_key produced by prepare_upload includes
the caller's user_id, and confirm_upload rejects keys outside that
prefix — without the check a client could confirm an arbitrary key
already in the bucket.
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
from domains.providers.models import ProviderProfile
from domains.providers.portfolio_photo import ProviderPortfolioPhoto
from domains.users.models import User
from domains.users.provider_portfolio_schemas import (
    ALLOWED_PORTFOLIO_MIME_TYPES,
    MAX_PORTFOLIO_PHOTO_SIZE_BYTES,
    MAX_PORTFOLIO_PHOTOS_PER_PROVIDER,
)
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


class PortfolioServiceError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


class ProviderPortfolioService:
    def __init__(self, db: AsyncSession, audit_ctx: AuditContext) -> None:
        self.db = db
        self.audit_ctx = audit_ctx
        self.audit_repo = AuditRepository(db)
        self._adapter: FileStorageAdapter = get_public_storage()

    # ─── Guards ─────────────────────────────────────────────────────────────

    async def _require_provider(self, user: User) -> None:
        """Every portfolio operation requires an activated provider
        profile. We don't 404 silently — surface a clear
        conflict-style error so the frontend can route the user to
        the activation flow."""
        pp = (await self.db.execute(
            select(ProviderProfile).where(ProviderProfile.user_id == user.id)
        )).scalar_one_or_none()
        if pp is None:
            raise PortfolioServiceError(
                status.HTTP_409_CONFLICT,
                "conflict",
                "Activate provider mode before managing your portfolio.",
            )

    # ─── List ───────────────────────────────────────────────────────────────

    async def list_for_user(self, user: User) -> list[ProviderPortfolioPhoto]:
        await self._require_provider(user)
        rows = (await self.db.scalars(
            select(ProviderPortfolioPhoto)
            .where(ProviderPortfolioPhoto.provider_user_id == user.id)
            .order_by(
                ProviderPortfolioPhoto.sort_order.asc(),
                ProviderPortfolioPhoto.created_at.asc(),
            )
        )).all()
        return list(rows)

    # ─── upload-url ─────────────────────────────────────────────────────────

    async def prepare_upload(
        self, user: User, mime_type: str, size_bytes: int,
    ) -> PresignedUpload:
        await self._require_provider(user)

        if mime_type not in ALLOWED_PORTFOLIO_MIME_TYPES:
            raise PortfolioServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"mime_type must be one of {sorted(ALLOWED_PORTFOLIO_MIME_TYPES)}",
            )
        if size_bytes <= 0 or size_bytes > MAX_PORTFOLIO_PHOTO_SIZE_BYTES:
            raise PortfolioServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"size_bytes must be in 1..{MAX_PORTFOLIO_PHOTO_SIZE_BYTES}",
            )

        photo_count = await self.db.scalar(
            select(func.count())
            .select_from(ProviderPortfolioPhoto)
            .where(ProviderPortfolioPhoto.provider_user_id == user.id)
        ) or 0
        if photo_count >= MAX_PORTFOLIO_PHOTOS_PER_PROVIDER:
            raise PortfolioServiceError(
                status.HTTP_409_CONFLICT,
                "conflict",
                f"Portfolio cap reached ({MAX_PORTFOLIO_PHOTOS_PER_PROVIDER}).",
            )

        ext = _MIME_TO_EXT.get(mime_type, "bin")
        token = secrets.token_urlsafe(16)
        key = f"provider_portfolio/{user.id}/{token}.{ext}"

        return await self._adapter.generate_upload_url(
            key,
            mime=mime_type,
            max_size=MAX_PORTFOLIO_PHOTO_SIZE_BYTES,
            ttl_seconds=3600,
        )

    # ─── confirm ────────────────────────────────────────────────────────────

    async def confirm_upload(
        self,
        user: User,
        s3_key: str,
        caption: str | None,
        tag: str | None,
    ) -> ProviderPortfolioPhoto:
        await self._require_provider(user)

        if not s3_key.startswith(f"provider_portfolio/{user.id}/"):
            raise PortfolioServiceError(
                status.HTTP_403_FORBIDDEN,
                "permission_denied",
                "s3_key does not belong to this provider.",
            )

        try:
            meta = await self._adapter.head_object(s3_key)
        except ObjectNotFound:
            raise PortfolioServiceError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "Upload not found at the requested key. Did the PUT succeed?",
            )

        if meta.content_type and meta.content_type not in ALLOWED_PORTFOLIO_MIME_TYPES:
            await self._adapter.delete_object(s3_key)
            raise PortfolioServiceError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "validation_failed",
                f"Uploaded content_type {meta.content_type!r} is not an allowed image type.",
            )

        if meta.size > MAX_PORTFOLIO_PHOTO_SIZE_BYTES:
            await self._adapter.delete_object(s3_key)
            raise PortfolioServiceError(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                "payload_too_large",
                f"Uploaded file exceeds the {MAX_PORTFOLIO_PHOTO_SIZE_BYTES}-byte limit.",
            )

        # Re-check cap (race window).
        photo_count = await self.db.scalar(
            select(func.count())
            .select_from(ProviderPortfolioPhoto)
            .where(ProviderPortfolioPhoto.provider_user_id == user.id)
        ) or 0
        if photo_count >= MAX_PORTFOLIO_PHOTOS_PER_PROVIDER:
            await self._adapter.delete_object(s3_key)
            raise PortfolioServiceError(
                status.HTTP_409_CONFLICT,
                "conflict",
                f"Portfolio cap reached ({MAX_PORTFOLIO_PHOTOS_PER_PROVIDER}).",
            )

        row = ProviderPortfolioPhoto(
            provider_user_id=user.id,
            s3_key=s3_key,
            caption=caption,
            tag=tag,
            sort_order=int(photo_count),
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    # ─── delete ─────────────────────────────────────────────────────────────

    async def delete(
        self, user: User, photo_id: uuid.UUID,
    ) -> None:
        await self._require_provider(user)
        row = (await self.db.execute(
            select(ProviderPortfolioPhoto)
            .where(
                ProviderPortfolioPhoto.id == photo_id,
                ProviderPortfolioPhoto.provider_user_id == user.id,
            )
        )).scalar_one_or_none()
        if row is None:
            raise PortfolioServiceError(
                status.HTTP_404_NOT_FOUND,
                "resource_not_found",
                "Portfolio photo not found.",
            )

        s3_key = row.s3_key
        await self.db.delete(row)
        await self.db.flush()

        try:
            await self._adapter.delete_object(s3_key)
        except Exception as exc:
            logger.warning("provider_portfolio: drop %s failed: %s", s3_key, exc)


def get_provider_portfolio_service(
    db: AsyncSession, request,
) -> ProviderPortfolioService:
    return ProviderPortfolioService(db=db, audit_ctx=get_audit_context(request))


def sign_portfolio_url(s3_key: str | None) -> str | None:
    """Build a download URL for a portfolio photo. Used by the router AND
    by the public detailer profile endpoint (Phase 5+ when that surfaces
    portfolios on the public page), so the URL format stays consistent."""
    if not s3_key:
        return None
    try:
        adapter = get_public_storage()
        return f"/storage/{adapter.bucket}/{s3_key}"
    except Exception as exc:
        logger.warning("provider_portfolio: failed to sign URL for %s: %s", s3_key, exc)
        return None
