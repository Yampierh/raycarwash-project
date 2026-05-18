"""
domains/users/provider_portfolio_router.py — /api/v1/users/me/
provider-portfolio (Phase 5 chunk Y3).

Endpoints per plan §2.12:
  GET    /me/provider-portfolio                list (sort_order ASC)
  POST   /me/provider-portfolio/upload-url     presigned PUT, cap-check
  POST   /me/provider-portfolio                confirm + INSERT
  DELETE /me/provider-portfolio/{photo_id}     drop + S3 cleanup

No step-up — portfolio photos are content, not credentials. The
activate-provider-mode requirement is enforced inside the service so
even the legacy /api/v1/detailers/me caller can't slip through with
just a role token.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Path, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from domains.auth.service import get_current_user
from domains.users.models import User
from domains.users.provider_portfolio_schemas import (
    PortfolioConfirmRequest,
    PortfolioPhotoResponse,
    PortfolioUploadUrlRequest,
    PortfolioUploadUrlResponse,
)
from domains.users.provider_portfolio_service import (
    get_provider_portfolio_service,
    sign_portfolio_url,
)
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(
    prefix="/api/v1/users/me/provider-portfolio",
    tags=["User Provider Portfolio"],
)


def _to_response(photo) -> PortfolioPhotoResponse:
    return PortfolioPhotoResponse(
        id=photo.id,
        provider_user_id=photo.provider_user_id,
        s3_key=photo.s3_key,
        caption=photo.caption,
        tag=photo.tag,
        sort_order=photo.sort_order,
        photo_url=sign_portfolio_url(photo.s3_key),
        created_at=photo.created_at,
    )


# ─── List ────────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=Envelope[list[PortfolioPhotoResponse]],
    summary="List portfolio photos for the caller (ordered by sort_order).",
    responses={
        409: {"description": "Provider mode not active — activate first."},
    },
)
async def list_portfolio(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[PortfolioPhotoResponse]]:
    service = get_provider_portfolio_service(db, request)
    photos = await service.list_for_user(current_user)
    return Envelope[list[PortfolioPhotoResponse]](
        data=[_to_response(p) for p in photos]
    )


# ─── upload-url ──────────────────────────────────────────────────────────────


@router.post(
    "/upload-url",
    response_model=Envelope[PortfolioUploadUrlResponse],
    summary="Step 1 of portfolio upload — returns a presigned URL. Rejects "
            "409 if the provider already holds the 30-photo cap.",
    responses={
        409: {"description": "Provider mode not active OR cap reached."},
        422: {"description": "mime_type or size_bytes outside allowed range."},
    },
)
async def upload_url(
    request: Request,
    body: PortfolioUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[PortfolioUploadUrlResponse]:
    service = get_provider_portfolio_service(db, request)
    presigned = await service.prepare_upload(
        current_user,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
    )
    return Envelope[PortfolioUploadUrlResponse](
        data=PortfolioUploadUrlResponse(
            url=presigned.url,
            method=presigned.method,
            headers=presigned.headers,
            s3_key=presigned.s3_key,
            expires_in=presigned.expires_in,
        )
    )


# ─── Confirm ─────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=Envelope[PortfolioPhotoResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Step 2: confirm an upload — HEADs the bytes, then INSERTs the "
            "ProviderPortfolioPhoto row at the next sort_order slot.",
    responses={
        403: {"description": "s3_key does not belong to this provider."},
        404: {"description": "Upload not found at the requested key."},
        409: {"description": "Cap reached between prepare and confirm."},
    },
)
async def confirm(
    request: Request,
    body: PortfolioConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[PortfolioPhotoResponse]:
    service = get_provider_portfolio_service(db, request)
    photo = await service.confirm_upload(
        current_user, body.s3_key, body.caption, body.tag,
    )
    await db.commit()
    return Envelope[PortfolioPhotoResponse](data=_to_response(photo))


# ─── Delete ──────────────────────────────────────────────────────────────────


@router.delete(
    "/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Hard-delete a portfolio photo + drop the S3 object.",
    responses={404: {"description": "Photo not found."}},
)
async def delete_photo(
    request: Request,
    photo_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = get_provider_portfolio_service(db, request)
    await service.delete(current_user, photo_id)
    await db.commit()
