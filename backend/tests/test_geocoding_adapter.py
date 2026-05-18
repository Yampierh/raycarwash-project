"""
tests/test_geocoding_adapter.py — Phase 4 chunk S.

Covers the GeocodingAdapter contract:
  - NominatimAdapter parses a happy-path response into GeocodeResult.
  - "No results" returns None (NOT GeocodingError).
  - 429 / 5xx raise GeocodingError so the service layer can decide policy.
  - Dependency factory returns NominatimAdapter in dev, raises in prod.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from infrastructure.geocoding.base import (
    GeocodeQuery,
    GeocodingError,
)
from infrastructure.geocoding.nominatim import NominatimAdapter


def _make_adapter_with_response(
    status_code: int = 200, body: str | list | dict = "[]"
) -> NominatimAdapter:
    """Inject an httpx MockTransport so the adapter never hits the network."""
    payload = body if isinstance(body, str) else json.dumps(body)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            content=payload.encode(),
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(handler)
    adapter = NominatimAdapter()

    # Monkeypatch httpx.AsyncClient invocation inside the adapter — the
    # cleanest way is to patch the AsyncClient constructor for the duration
    # of the call. We expose the transport via a closure on the adapter.
    adapter._test_transport = transport  # type: ignore[attr-defined]
    return adapter


@pytest.fixture
def query() -> GeocodeQuery:
    return GeocodeQuery(
        line1="1600 Amphitheatre Pkwy",
        line2=None,
        city="Mountain View",
        state="CA",
        zip_code="94043",
        country="US",
    )


def _patch_async_client_with(transport: httpx.MockTransport):
    """Return a context manager that swaps httpx.AsyncClient's default
    transport for our MockTransport. We patch the class used inside
    NominatimAdapter so the rate-limit sleep path is exercised normally."""
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs.pop("timeout", None)
        return real_async_client(transport=transport)

    return patch("infrastructure.geocoding.nominatim.httpx.AsyncClient", factory)


@pytest.mark.asyncio
async def test_nominatim_happy_path(query: GeocodeQuery):
    adapter = _make_adapter_with_response(
        200,
        [
            {
                "lat": "37.422",
                "lon": "-122.084",
                "display_name": "1600 Amphitheatre Pkwy, Mountain View, CA, USA",
                "importance": 0.62,
            }
        ],
    )
    with _patch_async_client_with(adapter._test_transport):  # type: ignore[attr-defined]
        result = await adapter.geocode(query)

    assert result is not None
    assert result.latitude == pytest.approx(37.422)
    assert result.longitude == pytest.approx(-122.084)
    assert "Mountain View" in result.formatted_address
    assert result.confidence == pytest.approx(0.62)


@pytest.mark.asyncio
async def test_nominatim_no_results_returns_none(query: GeocodeQuery):
    adapter = _make_adapter_with_response(200, [])
    with _patch_async_client_with(adapter._test_transport):  # type: ignore[attr-defined]
        result = await adapter.geocode(query)
    assert result is None


@pytest.mark.asyncio
async def test_nominatim_rate_limit_raises(query: GeocodeQuery):
    adapter = _make_adapter_with_response(429, "rate-limited")
    with _patch_async_client_with(adapter._test_transport):  # type: ignore[attr-defined]
        with pytest.raises(GeocodingError):
            await adapter.geocode(query)


@pytest.mark.asyncio
async def test_nominatim_5xx_raises(query: GeocodeQuery):
    adapter = _make_adapter_with_response(503, "down")
    with _patch_async_client_with(adapter._test_transport):  # type: ignore[attr-defined]
        with pytest.raises(GeocodingError):
            await adapter.geocode(query)


@pytest.mark.asyncio
async def test_nominatim_unexpected_4xx_returns_none(query: GeocodeQuery):
    """403/404 from a misconfigured proxy aren't system failures — fall back
    to "no match" so the caller can decide whether to ask the user to
    re-enter."""
    adapter = _make_adapter_with_response(404, "")
    with _patch_async_client_with(adapter._test_transport):  # type: ignore[attr-defined]
        result = await adapter.geocode(query)
    assert result is None


def test_dependency_factory_returns_nominatim_in_dev(monkeypatch):
    from app.core import dependencies as deps

    deps.get_geocoding_adapter.cache_clear()
    monkeypatch.setattr(
        deps.get_settings(), "RAYCARWASH_ENV", "development", raising=False
    )
    adapter = deps.get_geocoding_adapter()
    assert isinstance(adapter, NominatimAdapter)


def test_dependency_factory_raises_in_prod(monkeypatch):
    from app.core import dependencies as deps

    deps.get_geocoding_adapter.cache_clear()
    monkeypatch.setattr(
        deps.get_settings(), "RAYCARWASH_ENV", "production", raising=False
    )
    with pytest.raises(RuntimeError, match="not implemented"):
        deps.get_geocoding_adapter()
    deps.get_geocoding_adapter.cache_clear()


def test_geocode_query_serializes_omitting_blanks():
    q = GeocodeQuery(
        line1="100 Main",
        line2=None,
        city="Miami",
        state="FL",
        zip_code="33101",
        country="US",
    )
    assert q.as_single_line() == "100 Main, Miami, FL, 33101, US"


def test_geocode_query_includes_line2_when_present():
    q = GeocodeQuery(
        line1="100 Main",
        line2="Apt 5B",
        city="Miami",
        state="FL",
        zip_code="33101",
        country="US",
    )
    assert q.as_single_line() == "100 Main, Apt 5B, Miami, FL, 33101, US"
