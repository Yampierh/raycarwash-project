"""
domains/users/favorites_router.py — /api/v1/users/me/favorites/providers
(Phase 4 chunk V).

Endpoints per plan §2.10:
  GET    /me/favorites/providers                       list
  POST   /me/favorites/providers/{provider_user_id}    add (idempotent)
  DELETE /me/favorites/providers/{provider_user_id}    remove (idempotent)

No step-up — pinning a provider isn't a financial action. Audit log
records FAVORITE_ADDED / FAVORITE_REMOVED via AuditContext.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.middleware.audit_context import get_audit_context
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.service import get_current_user
from domains.providers.models import ProviderProfile
from domains.users.favorites_repository import FavoritesRepository
from domains.users.favorites_schemas import FavoriteProviderResponse
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = EnvelopeRouter(
    prefix="/api/v1/users/me/favorites",
    tags=["User Favorites"],
)


# ─── List ────────────────────────────────────────────────────────────────────


@router.get(
    "/providers",
    response_model=Envelope[list[FavoriteProviderResponse]],
    summary="List the user's favorited providers (newest first).",
)
async def list_favorites(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[list[FavoriteProviderResponse]]:
    repo = FavoritesRepository(db)
    rows = await repo.list_for_user(current_user.id)
    items = [
        FavoriteProviderResponse(
            provider_user_id=fav.provider_user_id,
            display_name=(pp.display_name if pp else None) or (
                # Fall back to provider's full_name minus PII concerns —
                # the User row is already what we own; ProviderProfile
                # just supplements it.
                user.full_name if user else None
            ),
            business_name=pp.business_name if pp else None,
            avatar_url=None,  # TODO(phase 5): _sign_url on user.avatar_s3_key
            rating=(float(pp.average_rating) if pp and pp.average_rating is not None else None),
            created_at=fav.created_at,
        )
        for fav, user, pp in rows
    ]
    return Envelope[list[FavoriteProviderResponse]](data=items)


# ─── Add ─────────────────────────────────────────────────────────────────────


@router.post(
    "/providers/{provider_user_id}",
    response_model=Envelope[FavoriteProviderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Pin a provider as favorite. Idempotent: re-favoring an already-"
            "pinned provider returns 201 with the existing row.",
    responses={
        404: {"description": "Provider user does not exist or is not a detailer."},
    },
)
async def add_favorite(
    request: Request,
    provider_user_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[FavoriteProviderResponse]:
    # Validate target exists AND is a detailer (otherwise users could
    # silently favorite arbitrary user IDs and clutter their list).
    provider_user = (await db.execute(
        select(User)
        .where(User.id == provider_user_id, User.is_deleted.is_(False))
    )).scalar_one_or_none()
    if provider_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resource_not_found", "message": "Provider not found."},
        )

    pp = (await db.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == provider_user_id)
    )).scalar_one_or_none()
    if pp is None:
        # Not a detailer — surface the same 404 so we don't reveal
        # account-shape details to enumerators.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resource_not_found", "message": "Provider not found."},
        )

    repo = FavoritesRepository(db)
    created = await repo.add(current_user.id, provider_user_id)

    if created:
        await AuditRepository(db).log(
            action=AuditAction.FAVORITE_ADDED,
            entity_type="client_favorite",
            entity_id=str(provider_user_id),
            actor_id=current_user.id,
            new_value={"provider_user_id": str(provider_user_id)},
            audit_ctx=get_audit_context(request),
        )

    await db.commit()

    # Re-read so the response carries the join-derived display fields.
    rows = await repo.list_for_user(current_user.id)
    fav, user, pp = next(
        (f, u, p) for f, u, p in rows if f.provider_user_id == provider_user_id
    )
    return Envelope[FavoriteProviderResponse](
        data=FavoriteProviderResponse(
            provider_user_id=fav.provider_user_id,
            display_name=(pp.display_name if pp else None) or (
                user.full_name if user else None
            ),
            business_name=pp.business_name if pp else None,
            avatar_url=None,
            rating=(float(pp.average_rating) if pp and pp.average_rating is not None else None),
            created_at=fav.created_at,
        )
    )


# ─── Remove ──────────────────────────────────────────────────────────────────


@router.delete(
    "/providers/{provider_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Unpin a provider. Idempotent: removing a non-favorite returns "
            "204 without raising.",
)
async def remove_favorite(
    request: Request,
    provider_user_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = FavoritesRepository(db)
    removed = await repo.remove(current_user.id, provider_user_id)
    if removed:
        await AuditRepository(db).log(
            action=AuditAction.FAVORITE_REMOVED,
            entity_type="client_favorite",
            entity_id=str(provider_user_id),
            actor_id=current_user.id,
            old_value={"provider_user_id": str(provider_user_id)},
            audit_ctx=get_audit_context(request),
        )
    await db.commit()
