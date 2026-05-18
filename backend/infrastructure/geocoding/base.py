"""
infrastructure/geocoding/base.py — GeocodingAdapter Protocol.

Concrete adapters: NominatimAdapter (dev, OSM free + rate-limited) and
GoogleMapsGeocodingAdapter (prod, TODO). Picked by environment in
app/core/dependencies.py.

The Profile system uses this to denormalize lat/lng + h3_index_r9 onto
UserAddress rows the moment they are written, so the matching engine and
booking flow can join on the H3 cell without re-geocoding.

Behaviour contract:
  - `geocode(address)` returns a GeocodeResult when the address resolves
    confidently, or None when the provider has no high-confidence match.
  - It MUST NOT raise on "address not found" — that's a user-input
    condition, not a system failure. Service-layer code decides whether
    to reject the request or store the row without coordinates.
  - It MAY raise GeocodingError on transport failures (timeout, 5xx,
    rate limit). Callers either retry or accept a row with lat/lng=None.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class GeocodingError(Exception):
    """Raised on transport failures (timeout, 5xx, rate limit). Never on
    "address not found" — that's modelled as `geocode() -> None`."""


@dataclass(frozen=True)
class GeocodeQuery:
    """Free-form components passed to the adapter. The adapter joins them
    into whatever query string the provider expects (Nominatim eats a
    single string; Google takes structured params)."""
    line1: str
    line2: str | None
    city: str
    state: str
    zip_code: str
    country: str = "US"

    def as_single_line(self) -> str:
        """Provider-agnostic flattening for adapters that take a string."""
        parts = [self.line1]
        if self.line2:
            parts.append(self.line2)
        parts.extend([self.city, self.state, self.zip_code, self.country])
        return ", ".join(p for p in parts if p)


@dataclass(frozen=True)
class GeocodeResult:
    latitude: float
    longitude: float
    # Free-form provider label of what was matched ("123 Main St, Miami, FL,
    # 33101, United States"). Useful for surfacing "did you mean…?" hints to
    # the user. Not stored permanently.
    formatted_address: str
    # Optional confidence/score the provider returned. 0..1 normalized when
    # available; None when the provider gives no numeric score.
    confidence: float | None = None


class GeocodingAdapter(Protocol):
    """Minimum surface Phase 4 needs. Reverse geocoding (lat/lng → address)
    is intentionally out of scope — no current screen requires it. Add a
    second protocol when one does, rather than expanding this one."""

    async def geocode(self, query: GeocodeQuery) -> GeocodeResult | None: ...
