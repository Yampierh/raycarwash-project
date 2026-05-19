"""
domains/users/active_role_service.py — Master plan Phase 6.

Implements the role-switch contract described in ADR-003:

  1. Target role must be in the caller's `user.user_roles`. Otherwise
     403 `permission_denied`.
  2. The caller's current refresh token is rotated (revoked + new one
     issued in the same family). A stolen refresh therefore cannot keep
     emitting access tokens with the previous role claim — Phase 5's
     `provider_profile_service` flow does NOT rotate, but that flow
     only adds a role; the active_role claim doesn't change there.
     Active-role switching DOES change the claim, so rotation is
     required.
  3. New access token carries `role: <target>` and the user's current
     `token_version`.
  4. Audit log captures ROLE_SWITCHED with {from, to}.

Deliberate departure from plan.md §2.3:
  The plan blocks switching to `detailer` when verification_status !=
  "approved". After E1 multi-profile, gating UI navigation by KYC
  creates a chicken-and-egg — a user who freshly created a detailer
  profile would be unable to view the detailer dashboard to complete
  KYC. KYC stays where it belongs: gating `is_active=true` (booking
  visibility), NOT role assignment or active-role switching.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.audit_context import AuditContext
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.refresh_token_repository import RefreshTokenRepository
from domains.auth.service import AuthService
from domains.users.active_role_schemas import (
    ActiveRoleResponse,
    ActiveRoleUpdateRequest,
)
from domains.users.models import User

logger = logging.getLogger(__name__)


# Roles a consumer-facing user can hold as their active context. admin is
# deliberately out — admins operate from /api/v1/admin/* with no role
# switcher in the consumer UI.
_SWITCHABLE_ROLES: frozenset[str] = frozenset({"client", "detailer", "mechanic"})


class ActiveRoleService:
    def __init__(self, db: AsyncSession, audit_ctx: AuditContext) -> None:
        self.db = db
        self.audit_ctx = audit_ctx
        self.refresh_repo = RefreshTokenRepository(db)
        self.audit_repo = AuditRepository(db)

    async def switch(
        self, user: User, body: ActiveRoleUpdateRequest,
    ) -> ActiveRoleResponse:
        target = body.role
        if target not in _SWITCHABLE_ROLES:
            # Pydantic's Literal already enforces this — defensive guard
            # in case the schema is loosened later.
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "bad_request",
                    "message": f"Role '{target}' cannot be set as active.",
                },
            )

        # 1. Caller must already hold the target role.
        held_roles = {ur.role.name for ur in (user.user_roles or [])}
        if target not in held_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "permission_denied",
                    "message": (
                        f"You don't hold the {target} role. Acquire it first "
                        "via the appropriate onboarding flow."
                    ),
                },
            )

        previous = user.active_role
        if previous == target:
            # No-op. Skip rotation + audit; the client got here because of
            # an idempotent UI tap. Return the same tokens? No — the caller
            # still expects a fresh pair. Honor the refresh rotation
            # contract: revoke + reissue so the caller has a clean session
            # to work with regardless of whether the role actually changed.
            pass

        # 2. Rotate the refresh token. Reuses AuthService.rotate_refresh_token
        # which atomically claims the old token + emits a new one in the
        # same family + detects theft (if the same raw token races).
        new_access_default, new_refresh = await AuthService.rotate_refresh_token(
            body.refresh_token, self.db,
        )
        # rotate_refresh_token emits an access token with the user's
        # primary_role. Override that here so the new access carries the
        # target role claim.
        new_access = AuthService.create_access_token(
            user.id, target, token_version=user.token_version or 1,
        )
        # Silence the unused-name warning — rotate_refresh_token still
        # had to mint the default access token internally; we discard it.
        del new_access_default

        # 3. Persist the new active_role.
        user.active_role = target
        await self.db.flush()

        # 4. Audit.
        await self.audit_repo.log(
            action=AuditAction.ROLE_SWITCHED,
            entity_type="user",
            entity_id=str(user.id),
            actor_id=user.id,
            old_value={"active_role": previous},
            new_value={"active_role": target},
            audit_ctx=self.audit_ctx,
        )

        logger.info(
            "active_role switched | user=%s from=%s to=%s",
            user.id, previous, target,
        )

        return ActiveRoleResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            active_role=target,
        )
