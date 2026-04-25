from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas import _BaseSchema, _BaseRequestSchema
from domains.vehicles.models import VehicleSize


class TimeSlotRead(_BaseSchema):
    start_time: datetime
    end_time: datetime
    is_available: bool


class AvailabilityRequest(_BaseSchema):
    request_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    service_id: uuid.UUID | None = Field(default=None)
    vehicle_size: VehicleSize | None = Field(default=None)


class LocationUpdate(_BaseRequestSchema):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    heading: float | None = Field(default=None, ge=0.0, lt=360.0)


class LocationResponse(_BaseSchema):
    user_id: uuid.UUID
    latitude: float
    longitude: float
    updated_at: datetime


class MatchingResult(_BaseSchema):
    user_id: uuid.UUID
    full_name: str
    bio: str | None = Field(default=None)
    years_of_experience: int | None = Field(default=None)
    service_radius_miles: int
    is_accepting_bookings: bool
    average_rating: float | None = Field(default=None)
    total_reviews: int
    distance_miles: float | None = Field(default=None)
    estimated_price: int
    estimated_duration: int
    available_slots: list[TimeSlotRead] = Field(default_factory=list)
