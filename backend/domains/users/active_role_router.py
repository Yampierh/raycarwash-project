"""
domains/users/active_role_router.py — /api/v1/users/me/active-role
(master plan Phase 6, ADR-003).

Single endpoint that lets a multi-role user swap which role the next JWT
carries in its `role` claim. Refresh token is rotated in the same call
(stolen-refresh ventana cerrada).
"""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.middleware.audit_context import get_audit_context
from domains.auth.service import get_current_user
from domains.users.active_role_schemas import (
    ActiveRoleResponse,
    ActiveRoleUpdateRequest,
)
from domains.users.active_role_service import ActiveRoleService
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope


router = EnvelopeRouter(
    prefix="/api/v1/users/me",
    tags=["User Active Role"],
)


@router.patch(
    "/active-role",
    response_model=Envelope[ActiveRoleResponse],
    summary=(
        "Switch the caller's active role. 403 if the target role is not "
        "assigned to the user. Rotates the refresh token (revokes the one "
        "in the body + emits a fresh pair) so stolen refreshes can't keep "
        "minting access tokens with the previous role claim."
    ),
    responses={
        401: {"description": "Authentication required, refresh token invalid, or rotation race lost."},
        403: {"description": "Target role is not assigned to the caller."},
    },
)
async def patch_active_role(
    request: Request,
    body: ActiveRoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[ActiveRoleResponse]:
    service = ActiveRoleService(db=db, audit_ctx=get_audit_context(request))
    payload = await service.switch(current_user, body)
    await db.commit()
    return Envelope[ActiveRoleResponse](data=payload)
