"""
infrastructure/geocoding/google.py — GoogleMapsGeocodingAdapter (prod, TODO).

Placeholder: the dev environment uses NominatimAdapter. When promoting to
production:

  1. Add `googlemaps` (sync) or use `httpx.AsyncClient` against
     https://maps.googleapis.com/maps/api/geocode/json directly.
  2. Read `settings.GOOGLE_MAPS_API_KEY` from environment.
  3. Map `results[0].geometry.location.{lat,lng}` →
     `GeocodeResult(latitude, longitude, …)`.
  4. Translate `results[0].partial_match=true` or
     `results[0].geometry.location_type="APPROXIMATE"` into a lower
     `confidence` so callers can decide whether to surface "did you mean…?".
  5. Raise GeocodingError on status `"OVER_QUERY_LIMIT"`, `"REQUEST_DENIED"`,
     `"UNKNOWN_ERROR"`; return None on `"ZERO_RESULTS"`.

Until then, importing this class will raise — keeps a forgotten env=production
deploy from silently dropping lat/lng on every address.
"""
from __future__ import annotations

from infrastructure.geocoding.base import (
    GeocodeQuery,
    GeocodeResult,
    GeocodingAdapter,
)


class GoogleMapsGeocodingAdapter(GeocodingAdapter):
    def __init__(self) -> None:
        # TODO(prod): wire settings.GOOGLE_MAPS_API_KEY and an httpx client.
        raise RuntimeError(
            "GoogleMapsGeocodingAdapter is not implemented yet. "
            "Implement infrastructure/geocoding/google.py or set "
            "RAYCARWASH_ENV=development to use NominatimAdapter."
        )

    async def geocode(self, query: GeocodeQuery) -> GeocodeResult | None:  # pragma: no cover
        # TODO(prod): implement against Google Maps Geocoding API per the
        # checklist in the module docstring.
        raise NotImplementedError
