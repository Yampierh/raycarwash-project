from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from shared.schemas import _BaseSchema, _BaseRequestSchema
from domains.vehicles.models import VehicleSize


class PaymentIntentRequest(_BaseSchema):
    appointment_id: uuid.UUID


class PaymentIntentResponse(_BaseSchema):
    payment_intent_id: str
    client_secret: str
    amount_cents: int
    currency: str = "usd"
    status: str


class FareEstimateRequest(_BaseRequestSchema):
    service_id: uuid.UUID
    vehicle_sizes: list[VehicleSize] = Field(..., min_length=1)
    client_lat: float = Field(..., ge=-90.0, le=90.0)
    client_lng: float = Field(..., ge=-180.0, le=180.0)


class FareEstimateResponse(_BaseSchema):
    fare_token: str
    base_price_cents: int
    surge_multiplier: Decimal
    estimated_price_cents: int
    nearby_detailers_count: int
    expires_at: datetime
