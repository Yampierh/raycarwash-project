"""
infrastructure/geocoding/nominatim.py — NominatimAdapter (dev only).

OSM Nominatim is free but rate-limited to ~1 req/s and forbids heavy use
without a self-hosted instance. Suitable for development; production must
swap to GoogleMapsGeocodingAdapter (or a self-hosted Nominatim mirror).

Usage policy compliance: requests carry a UA identifying RayCarWash, and
the adapter sleeps between calls so a single process can't exceed the
free tier. If the dev workflow ever needs to batch addresses, point at
a docker-compose Nominatim service instead.
"""
from __future__ import annotations

import asyncio
import json
import logging

import httpx

from infrastructure.geocoding.base import (
    GeocodeQuery,
    GeocodeResult,
    GeocodingAdapter,
    GeocodingError,
)

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Polite identifier as required by the OSM Nominatim usage policy.
USER_AGENT = "RayCarWash-Dev/1.0 (contact: dev@raycarwash.local)"

# Minimum spacing between requests for the shared instance. The class
# guards a single client; multiple processes obviously can't coordinate
# through this lock — that's another reason it's dev-only.
_MIN_INTERVAL_SECONDS = 1.1


class NominatimAdapter(GeocodingAdapter):
    def __init__(self, *, timeout_seconds: float = 5.0) -> None:
        self._timeout = timeout_seconds
        self._last_call_at: float = 0.0
        self._lock = asyncio.Lock()

    async def geocode(self, query: GeocodeQuery) -> GeocodeResult | None:
        async with self._lock:
            await self._respect_rate_limit()
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.get(
                        NOMINATIM_URL,
                        params={
                            "q": query.as_single_line(),
                            "format": "jsonv2",
                            "limit": 1,
                            "addressdetails": 0,
                        },
                        headers={"User-Agent": USER_AGENT},
                    )
            except httpx.HTTPError as exc:
                logger.warning("nominatim transport failure: %s", exc)
                raise GeocodingError(str(exc)) from exc

            self._last_call_at = asyncio.get_event_loop().time()

        if resp.status_code == 429:
            raise GeocodingError("rate-limited by Nominatim")
        if resp.status_code >= 500:
            raise GeocodingError(f"upstream {resp.status_code}")
        if resp.status_code != 200:
            logger.warning("nominatim unexpected status %s: %s", resp.status_code, resp.text[:200])
            return None

        try:
            data = resp.json()
        except json.JSONDecodeError:
            logger.warning("nominatim returned non-JSON payload")
            return None

        if not isinstance(data, list) or not data:
            return None

        first = data[0]
        try:
            lat = float(first["lat"])
            lng = float(first["lon"])
        except (KeyError, TypeError, ValueError):
            return None

        # Nominatim's "importance" is roughly 0..1 — close enough to use as
        # a confidence proxy without rescaling.
        importance = first.get("importance")
        confidence = float(importance) if isinstance(importance, (int, float)) else None

        return GeocodeResult(
            latitude=lat,
            longitude=lng,
            formatted_address=first.get("display_name", query.as_single_line()),
            confidence=confidence,
        )

    async def _respect_rate_limit(self) -> None:
        now = asyncio.get_event_loop().time()
        delta = now - self._last_call_at
        if delta < _MIN_INTERVAL_SECONDS:
            await asyncio.sleep(_MIN_INTERVAL_SECONDS - delta)
