"""
domains/users/favorites_schemas.py — shapes for
`/api/v1/users/me/favorites/providers/*` (Phase 4 chunk V).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from shared.schemas import _BaseSchema


class FavoriteProviderResponse(_BaseSchema):
    """One favorite — provider identity + when it was pinned.

    `display_name` / `avatar_url` / `rating` join in from ProviderProfile;
    None when the provider hasn't yet completed their detailer profile
    (rare, but possible if they were favorited mid-onboarding)."""
    provider_user_id: uuid.UUID
    display_name: str | None = None
    business_name: str | None = None
    avatar_url: str | None = None
    rating: float | None = None
    created_at: datetime
