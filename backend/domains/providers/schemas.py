from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from shared.schemas import _BaseSchema, _BaseRequestSchema

_IANA_TIMEZONE_PATTERN = r"^[A-Za-z]+(/[A-Za-z_]+)+$"
_VALID_DAYS = frozenset({"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"})


class WorkingHoursDay(BaseModel):
    start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    enabled: bool = True

    @model_validator(mode="after")
    def start_and_end_required_when_enabled(self) -> WorkingHoursDay:
        if self.enabled and (self.start is None or self.end is None):
            raise ValueError("start and end times are required when the day is enabled.")
        return self


class ProviderProfileRead(_BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    bio: str | None = Field(default=None)
    years_of_experience: int | None = Field(default=None)
    is_accepting_bookings: bool
    service_radius_miles: int
    timezone: str = Field(default="America/Indiana/Indianapolis")
    working_hours: dict
    average_rating: float | None = Field(default=None)
    total_reviews: int
    created_at: datetime


class DetailerMeRead(_BaseSchema):
    user_id: uuid.UUID
    full_name: str
    bio: str | None = Field(default=None)
    years_of_experience: int | None = Field(default=None)
    service_radius_miles: int
    is_accepting_bookings: bool
    average_rating: float | None = Field(default=None)
    total_reviews: int
    total_earnings_cents: int = Field(default=0)
    total_services: int = Field(default=0)
    specialties: list[str] = Field(default_factory=list)
    created_at: datetime


class DetailerServiceRead(_BaseSchema):
    service_id: uuid.UUID
    name: str
    description: str | None = Field(default=None)
    base_price_cents: int
    custom_price_cents: int | None = Field(default=None)
    is_active: bool


class DetailerServiceUpdate(_BaseRequestSchema):
    is_active: bool
    custom_price_cents: int | None = Field(default=None, gt=0)


class DetailerStatusUpdate(BaseModel):
    is_accepting_bookings: bool


class ProviderProfileCreate(_BaseRequestSchema):
    bio: str | None = Field(default=None, max_length=1000)
    years_of_experience: int | None = Field(default=None, ge=0, le=50)
    service_radius_miles: int = Field(default=25, ge=1, le=100)
    timezone: str = Field(default="America/Indiana/Indianapolis", pattern=_IANA_TIMEZONE_PATTERN)
    working_hours: dict[str, WorkingHoursDay] | None = Field(default=None)
    specialties: list[str] | None = Field(default=None)

    @field_validator("working_hours", mode="before")
    @classmethod
    def validate_working_hours_keys(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        invalid = set(v.keys()) - _VALID_DAYS
        if invalid:
            raise ValueError(f"Invalid day keys: {invalid}. Allowed: {sorted(_VALID_DAYS)}.")
        return v


class ProviderProfileUpdate(_BaseRequestSchema):
    bio: str | None = Field(default=None, max_length=1000)
    years_of_experience: int | None = Field(default=None, ge=0, le=50)
    is_accepting_bookings: bool | None = Field(default=None)
    service_radius_miles: int | None = Field(default=None, ge=1, le=100)
    timezone: str | None = Field(default=None, pattern=_IANA_TIMEZONE_PATTERN)
    working_hours: dict[str, WorkingHoursDay] | None = Field(default=None)

    @field_validator("working_hours", mode="before")
    @classmethod
    def validate_working_hours_keys(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        invalid = set(v.keys()) - _VALID_DAYS
        if invalid:
            raise ValueError(f"Invalid day keys: {invalid}. Allowed: {sorted(_VALID_DAYS)}.")
        return v


class DetailerPublicRead(_BaseSchema):
    user_id: uuid.UUID
    full_name: str
    bio: str | None = Field(default=None)
    years_of_experience: int | None = Field(default=None)
    service_radius_miles: int
    is_accepting_bookings: bool
    average_rating: float | None = Field(default=None)
    total_reviews: int
    distance_miles: float | None = Field(default=None)
