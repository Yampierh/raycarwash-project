from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from shared.schemas import _BaseSchema, _BaseRequestSchema
from domains.appointments.models import AppointmentStatus
from domains.vehicles.models import VehicleSize


class AppointmentVehicleCreate(BaseModel):
    vehicle_id: uuid.UUID
    service_id: uuid.UUID
    addon_ids: list[uuid.UUID] = Field(default_factory=list)


class AppointmentCreate(_BaseRequestSchema):
    detailer_id: uuid.UUID
    scheduled_time: datetime
    service_address: str = Field(..., min_length=5, max_length=255)
    service_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    service_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    client_notes: str | None = Field(default=None, max_length=2000)

    # New multi-vehicle format
    vehicles: list[AppointmentVehicleCreate] | None = Field(default=None, min_length=1, max_length=10)

    # Legacy compat
    vehicle_id: uuid.UUID | None = Field(default=None)
    vehicle_ids: list[uuid.UUID] | None = Field(default=None, min_length=1, max_length=10)
    addon_ids: list[uuid.UUID] = Field(default_factory=list)
    service_id: uuid.UUID | None = Field(default=None)

    @field_validator("scheduled_time", mode="after")
    @classmethod
    def must_be_utc_and_future(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("scheduled_time debe incluir zona horaria (UTC).")
        utc_value = v.astimezone(timezone.utc)
        if utc_value <= datetime.now(timezone.utc):
            raise ValueError("scheduled_time debe ser una fecha futura.")
        return utc_value

    @model_validator(mode="after")
    def normalize_vehicle_fields(self) -> AppointmentCreate:
        if self.vehicles:
            return self
        if self.vehicle_ids:
            vids = self.vehicle_ids
        elif self.vehicle_id:
            vids = [self.vehicle_id]
        else:
            raise ValueError("Proporciona 'vehicles' o 'vehicle_id'/'vehicle_ids'.")
        if not self.service_id:
            raise ValueError("service_id es requerido con el formato legado.")
        object.__setattr__(self, "vehicles", [
            AppointmentVehicleCreate(vehicle_id=vid, service_id=self.service_id, addon_ids=self.addon_ids)
            for vid in vids
        ])
        return self

    @model_validator(mode="after")
    def validate_coordinates_both_or_none(self) -> AppointmentCreate:
        lat, lon = self.service_latitude, self.service_longitude
        if (lat is None) != (lon is None):
            raise ValueError("service_latitude y service_longitude deben proporcionarse juntos.")
        return self


class _VehicleSnap(_BaseSchema):
    make: str
    model: str
    body_class: str | None = Field(default=None)
    color: str


class AppointmentVehicleRead(_BaseSchema):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    vehicle_size: VehicleSize
    price_cents: int
    duration_minutes: int
    vehicle: _VehicleSnap | None = Field(default=None)


class AppointmentAddonRead(_BaseSchema):
    id: uuid.UUID
    addon_id: uuid.UUID
    price_cents: int
    duration_minutes: int


class _ClientSnap(_BaseSchema):
    full_name: str
    phone: str | None = Field(default=None)


class _DetailerSnap(_BaseSchema):
    full_name: str


class AppointmentRead(_BaseSchema):
    id: uuid.UUID
    status: AppointmentStatus
    scheduled_time: datetime
    estimated_end_time: datetime
    travel_buffer_end_time: datetime
    service_address: str | None = Field(default=None)
    client_notes: str | None = Field(default=None)
    detailer_notes: str | None = Field(default=None)
    service_latitude: float | None = Field(default=None)
    service_longitude: float | None = Field(default=None)

    estimated_price_cents: int = Field(alias="estimated_price")
    actual_price_cents: int | None = Field(default=None, alias="actual_price")

    arrived_at: datetime | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    stripe_payment_intent_id: str | None = Field(default=None)

    client: _ClientSnap | None = Field(default=None)
    detailer: _DetailerSnap | None = Field(default=None)
    vehicles: list[AppointmentVehicleRead] = Field(default_factory=list)

    client_id: uuid.UUID
    detailer_id: uuid.UUID
    vehicle_id: uuid.UUID | None = Field(default=None)
    service_id: uuid.UUID | None = Field(default=None)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True, str_strip_whitespace=True)


class AppointmentStatusUpdate(_BaseSchema):
    status: AppointmentStatus
    detailer_notes: str | None = Field(default=None, max_length=2000)
    actual_price: int | None = Field(default=None, gt=0)


class RefundResponse(_BaseSchema):
    appointment_id: uuid.UUID
    refund_amount_cents: int
    refund_policy_applied: str
    stripe_refund_id: str | None = Field(default=None)
