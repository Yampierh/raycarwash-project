"""
domains/users/active_role_schemas.py — Wire shapes for the active-role
switcher (master plan Phase 6, ADR-003).

`PATCH /api/v1/users/me/active-role` lets a multi-role user swap which
role the next JWT carries in its `role` claim. Refresh token is rotated
in the same call so a stolen refresh can't keep emitting access tokens
with the previous role.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from shared.schemas import _BaseSchema, _BaseRequestSchema


# Accepted active roles. "admin" is deliberately excluded — admins use
# /api/v1/admin/* exclusively and don't participate in the consumer
# role-switch UI. Mechanic landed in E1.C; before that it was just
# client + detailer.
_SwitchableRole = Literal["client", "detailer", "mechanic"]


class ActiveRoleUpdateRequest(_BaseRequestSchema):
    role: _SwitchableRole = Field(
        ..., description="Target active role for the caller. Must already be assigned to the user.",
    )
    refresh_token: str = Field(
        ..., min_length=1,
        description=(
            "The caller's current refresh token. Revoked atomically as part of "
            "the switch so a stolen refresh can't continue emitting access "
            "tokens with the previous role claim (ADR-003)."
        ),
    )


class ActiveRoleResponse(_BaseSchema):
    access_token: str
    refresh_token: str
    active_role: _SwitchableRole
