"""
domains/users/router.py — `/api/v1/users/*` endpoints.

Phase 1 ships the Profile Hub (ADR-002b):
  GET   /api/v1/users/me?include=<tokens>
  PATCH /api/v1/users/me

Registration still lives at POST /auth/register; admin user-management
endpoints live in /api/v1/admin/users/* (domains/admin/router.py).
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.envelope_router import EnvelopeRouter
from app.core.step_up import StepUpRequiredError, is_step_up_recent
from domains.auth.service import get_current_user
from domains.users.hub_schemas import HubProfilePatch, HubResponse
from domains.users.hub_service import ProfileHubService
from domains.users.include_spec import BadIncludeToken, IncludeSpec
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope, Meta

logger = logging.getLogger(__name__)

router = EnvelopeRouter(prefix="/api/v1/users", tags=["Users"])

# Compatibility shim: a few legacy imports do `from domains.users.router import router`
# and expect an APIRouter. EnvelopeRouter is one, so this works out of the box.


# ─── GET /users/me ────────────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=Envelope[HubResponse],
    summary="Profile Hub: composite response keyed by ?include= tokens.",
    description=(
        "Always returns `user` and `verification_badges`. Other blocks "
        "(`profile`, `vehicles`, `favorites`, `sessions`, `security`, `provider`, "
        "`addresses`, `payment_methods`, `preferences`, `notifications`, `stats`) "
        "are opt-in via `?include=token1,token2`. Sensitive tokens "
        "(`security`, `sessions`) require recent step-up; clients can pass "
        "`?on_step_up=skip` to receive a 200 with those blocks omitted and a "
        "`meta.skipped_due_to_step_up` marker."
    ),
)
async def get_me(
    request: Request,
    include: Annotated[str | None, Query(description="Comma-separated include tokens.")] = None,
    on_step_up: Annotated[str | None, Query(description="Pass `skip` to omit sensitive blocks instead of raising 401.")] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[HubResponse]:
    # Echo current user into request.state so step_up.require_step_up
    # (and any future dependency) can read it via `request.state.user`.
    request.state.user = current_user

    skip = (on_step_up or "").lower() == "skip"
    roles = {ur.role.name for ur in (current_user.user_roles or [])}

    try:
        spec = IncludeSpec.parse(include, roles=roles)
    except BadIncludeToken as exc:
        from domains.users.include_spec import ALL_TOKENS
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "bad_request",
                "message": f"unknown include token: {exc.token!r}",
                "details": [
                    {"field": "include", "reason": f"valid tokens: {sorted(ALL_TOKENS)}"}
                ],
            },
        )

    # Sensitive tokens + no step-up + no skip → 401 step_up_required.
    if spec.sensitive and not skip:
        if not await is_step_up_recent(request, current_user):
            raise StepUpRequiredError(requires=sorted(spec.sensitive))

    service = ProfileHubService(db, request)
    hub, populated, skipped = await service.build(
        current_user, spec, on_step_up_skip=skip,
    )

    meta = Meta(
        includes=sorted(populated) or None,
        skipped_due_to_step_up=sorted(skipped) or None,
    )
    return Envelope[HubResponse](data=hub, meta=meta)


# ─── PATCH /users/me ──────────────────────────────────────────────────────────


@router.patch(
    "/me",
    response_model=Envelope[HubResponse],
    summary="Update profile-block fields (name, pronouns, language, timezone).",
    description=(
        "Mutates only fields that live in the `profile` block. Email and phone "
        "changes go through `/users/me/email/*` and `/users/me/phone/*` (Phase 3). "
        "Returns the updated Hub with `?include=profile,stats` populated."
    ),
)
async def patch_me(
    request: Request,
    body: HubProfilePatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Envelope[HubResponse]:
    request.state.user = current_user

    service = ProfileHubService(db, request)
    await service.update_profile_fields(
        current_user,
        first_name=body.first_name,
        last_name=body.last_name,
        pronouns=body.pronouns,
        language=body.language,
        timezone_name=body.timezone,
        zip_code=body.zip_code,
    )

    # Return the updated profile + stats so the client can replace its cache
    # in a single round trip.
    spec = IncludeSpec.parse("profile,stats", roles={ur.role.name for ur in (current_user.user_roles or [])})
    hub, populated, skipped = await service.build(current_user, spec)
    return Envelope[HubResponse](
        data=hub,
        meta=Meta(
            includes=sorted(populated) or None,
            skipped_due_to_step_up=sorted(skipped) or None,
        ),
    )


# ─── Cache key helper (Phase 9 wiring) ────────────────────────────────────────


def _hub_cache_key(user_id, token_version: int, spec: IncludeSpec) -> str:
    """
    `profile:hub:{user_id}:{token_version}:{include_hash}` — exposed for the
    Phase 9 Redis cache layer. Hash the sorted tokens so order doesn't
    fragment cache entries.
    """
    token_blob = json.dumps(sorted(spec.effective), separators=(",", ":")).encode()
    digest = hashlib.sha256(token_blob).hexdigest()[:16]
    return f"profile:hub:{user_id}:{token_version}:{digest}"
