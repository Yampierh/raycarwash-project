from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas import _BaseSchema, _BaseRequestSchema


class ReviewCreate(_BaseRequestSchema):
    appointment_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewRead(_BaseSchema):
    id: uuid.UUID
    appointment_id: uuid.UUID
    reviewer_id: uuid.UUID
    detailer_id: uuid.UUID
    rating: int
    comment: str | None = Field(default=None)
    created_at: datetime
