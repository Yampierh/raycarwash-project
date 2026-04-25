from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas import _BaseSchema
from domains.services_catalog.models import ServiceCategory


class ServiceRead(_BaseSchema):
    id: uuid.UUID
    name: str
    description: str | None = Field(default=None)
    category: ServiceCategory
    base_price_cents: int
    base_duration_minutes: int
    price_small: int
    price_medium: int
    price_large: int
    price_xl: int
    duration_small_minutes: int
    duration_medium_minutes: int
    duration_large_minutes: int
    duration_xl_minutes: int
    is_active: bool
    created_at: datetime


class AddonRead(_BaseSchema):
    id: uuid.UUID
    name: str
    description: str | None = Field(default=None)
    price_cents: int
    duration_minutes: int
    is_active: bool
    created_at: datetime
