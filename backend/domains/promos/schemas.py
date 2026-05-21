"""
domains/promos/schemas.py — wire contract for promo lookup + preview.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


PromoDiscountType = Literal["fixed_cents", "percent"]


class PromoCodeRead(BaseModel):
    """Public-safe view of a promo code. Excludes admin-only fields like
    `max_redemptions` global cap and the redemption counter."""

    id: uuid.UUID
    code: str
    description: Optional[str] = None
    discount_type: PromoDiscountType
    discount_amount: int
    min_order_cents: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool

    # Per-user eligibility — populated when the lookup is authenticated.
    eligible: Optional[bool] = None
    ineligible_reason: Optional[str] = None
    remaining_per_user: Optional[int] = None

    model_config = {"from_attributes": True}


class PromoPreviewRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=32)
    subtotal_cents: int = Field(..., ge=0)


class PromoPreviewResponse(BaseModel):
    code: str
    eligible: bool
    discount_cents: int
    final_cents: int
    reason: Optional[str] = None  # populated when eligible=False
