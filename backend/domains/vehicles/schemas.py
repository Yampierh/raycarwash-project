from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field, computed_field, field_validator

from shared.schemas import _BaseSchema, _BaseRequestSchema


class VehicleCreate(_BaseRequestSchema):
    make: str = Field(..., min_length=1, max_length=60)
    model: str = Field(..., min_length=1, max_length=60)
    year: int = Field(..., ge=1970, le=2030)
    vin: str | None = Field(default=None, min_length=17, max_length=17)
    series: str | None = Field(default=None, max_length=60)
    body_class: str = Field(..., min_length=1, max_length=60)
    color: str | None = Field(default=None, max_length=40)
    license_plate: str | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("license_plate", mode="before")
    @classmethod
    def uppercase_plate(cls, v: str | None) -> str | None:
        return v.upper() if v else v


class VehicleRead(_BaseSchema):
    id: uuid.UUID
    owner_id: uuid.UUID
    make: str
    model: str
    year: int
    vin: str | None = Field(default=None)
    series: str | None = Field(default=None)
    body_class: str | None = Field(default=None)
    color: str
    license_plate: str
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def suggested_size(self) -> str | None:
        if not self.body_class:
            return None
        from infrastructure.nhtsa.client import map_body_to_size
        return map_body_to_size(self.body_class).value
