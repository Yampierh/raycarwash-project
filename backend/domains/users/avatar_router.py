"""
domains/users/avatar_router.py — /api/v1/users/me/avatar/* and /cover/*.

Three endpoints per kind:
  POST   /avatar/upload-url    → presigned URL
  POST   /avatar               → confirm (HEAD-verifies the bytes landed)
  DELETE /avatar               → remove + null the column

Cover endpoints mirror avatar but are gated to detailers (they're a public
detail-page hero, not a user-level field).

Step-up is NOT required — avatar churn is routine. The audit log entry
captured by AvatarService carries the actor + IP + UA for forensics.
"""
from __future__ import annotations

from fastapi import Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.exception_handlers import BusinessError
from domains.auth.service import get_current_user
from domains.users.avatar_schemas import (
    AvatarConfirmResponse,
    ConfirmUploadRequest,
    UploadUrlRequest,
    UploadUrlResponse,
)
from domains.users.avatar_service import AvatarService
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(prefix="/api/v1/users/me", tags=["Users · Avatar"])


def _require_detailer(user: User) -> None:
    """Cover endpoints — only detailers have a public hero card."""
    if not user.is_detailer():
        raise BusinessError(
            code="permission_denied",
            message="Cover images are only available for detailer accounts.",
            status_code=status.HTTP_403_FORBIDDEN,
        )


# ─── /avatar ─────────────────────────────────────────────────────────────────


@router.post(
    "/avatar/upload-url",
    response_model=Envelope[UploadUrlResponse],
    summary="Get a presigned upload URL for the user's avatar.",
)
async def avatar_upload_url(
    body: UploadUrlRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[UploadUrlResponse]:
    request.state.user = current_user
    service = AvatarService(db, request)
    presigned = await service.prepare_upload(
        current_user, body.mime_type, body.size_bytes, kind="avatar",
    )
    return Envelope(data=UploadUrlResponse(
        url=presigned.url,
        method=presigned.method,
        headers=presigned.headers,
        s3_key=presigned.s3_key,
        expires_in=presigned.expires_in,
    ))


@router.post(
    "/avatar",
    response_model=Envelope[AvatarConfirmResponse],
    summary="Confirm the avatar upload and persist it on the user.",
)
async def avatar_confirm(
    body: ConfirmUploadRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[AvatarConfirmResponse]:
    request.state.user = current_user
    service = AvatarService(db, request)
    avatar_url = await service.confirm_upload(current_user, body.s3_key, kind="avatar")
    return Envelope(data=AvatarConfirmResponse(avatar_url=avatar_url))


@router.delete(
    "/avatar",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove the user's avatar.",
)
async def avatar_delete(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    request.state.user = current_user
    service = AvatarService(db, request)
    await service.delete(current_user, kind="avatar")


# ─── /cover (detailers only) ─────────────────────────────────────────────────


@router.post(
    "/cover/upload-url",
    response_model=Envelope[UploadUrlResponse],
    summary="Get a presigned upload URL for the detailer's cover image.",
)
async def cover_upload_url(
    body: UploadUrlRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[UploadUrlResponse]:
    request.state.user = current_user
    _require_detailer(current_user)
    service = AvatarService(db, request)
    presigned = await service.prepare_upload(
        current_user, body.mime_type, body.size_bytes, kind="cover",
    )
    return Envelope(data=UploadUrlResponse(
        url=presigned.url,
        method=presigned.method,
        headers=presigned.headers,
        s3_key=presigned.s3_key,
        expires_in=presigned.expires_in,
    ))


@router.post(
    "/cover",
    response_model=Envelope[AvatarConfirmResponse],
    summary="Confirm the cover upload and persist it.",
)
async def cover_confirm(
    body: ConfirmUploadRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[AvatarConfirmResponse]:
    request.state.user = current_user
    _require_detailer(current_user)
    service = AvatarService(db, request)
    cover_url = await service.confirm_upload(current_user, body.s3_key, kind="cover")
    return Envelope(data=AvatarConfirmResponse(cover_url=cover_url))


@router.delete(
    "/cover",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Remove the detailer's cover image.",
)
async def cover_delete(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    request.state.user = current_user
    _require_detailer(current_user)
    service = AvatarService(db, request)
    await service.delete(current_user, kind="cover")
