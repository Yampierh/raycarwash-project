"""
infrastructure/nhtsa/client.py

NHTSA vPIC VIN decode API + canonical VehicleSize mapping.
Single source of truth for body-class → pricing tier conversion.
"""
from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from domains.vehicles.models import VehicleSize

logger = logging.getLogger(__name__)

NHTSA_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"


def map_body_to_size(body_class: str | None) -> VehicleSize:
    """
    Map an NHTSA BodyClass string to a VehicleSize pricing tier.

    SMALL  (×1.0) — Sedan, Coupe, Hatchback, Convertible
    MEDIUM (×1.2) — SUV, Crossover, CUV
    LARGE  (×1.5) — Pickup truck
    XL     (×2.0) — Van, Minivan, Sprinter
    """
    bc = (body_class or "").lower().strip()

    if "pickup" in bc:
        return VehicleSize.LARGE

    if "utility vehicle" in bc or "suv" in bc or "crossover" in bc or "cuv" in bc:
        return VehicleSize.MEDIUM

    if "van" in bc or "minivan" in bc:
        return VehicleSize.XL

    return VehicleSize.SMALL


# ── Plan 24 §3 C-1 — model-keyword heuristic ──────────────────────────
#
# `map_body_to_size` requires an NHTSA `BodyClass` lookup (needs a VIN).
# The customer-signup price-preview endpoint runs BEFORE the user has a
# VIN — they've only entered year/make/model. We approximate with a
# keyword search on the model name. Coverage is best-effort, weighted
# to the popular nameplates in our launch markets. Unknown models fall
# back to SMALL (cheapest tier) so we never UNDER-quote a customer.

_MODEL_KEYWORD_TO_SIZE: list[tuple[tuple[str, ...], VehicleSize]] = [
    # XL — vans, minivans, full-size haulers
    (
        ("transit", "sprinter", "pacifica", "odyssey", "sienna",
         "carnival", "promaster"),
        VehicleSize.XL,
    ),
    # LARGE — pickups + full-size SUVs (suburban, tahoe, etc.)
    (
        ("f-150", "f150", "f-250", "f-350", "silverado", "sierra",
         "ram 1500", "tundra", "tacoma", "ranger", "colorado",
         "frontier", "ridgeline", "titan", "gladiator",
         "suburban", "tahoe", "yukon", "expedition", "armada",
         "sequoia", "wagoneer"),
        VehicleSize.LARGE,
    ),
    # MEDIUM — mid-size SUVs / crossovers / CUVs
    (
        ("pilot", "passport", "rav4", "rav-4", "cr-v", "crv",
         "highlander", "4runner", "explorer", "edge",
         "cherokee", "grand cherokee", "compass", "wrangler",
         "outback", "ascent", "forester",
         "rogue", "murano", "pathfinder",
         "tucson", "santa fe", "kona", "telluride", "palisade",
         "sorento", "sportage", "ev6",
         "rx", "nx", "ux",
         "x3", "x5", "x7", "ix",
         "q5", "q7", "q8", "e-tron",
         "glc", "gle", "gls", "eqe", "eqs",
         "model y", "model x", "id.4", "id4", "mach-e",
         "cx-5", "cx-9", "cx-30", "cx-50"),
        VehicleSize.MEDIUM,
    ),
    # SMALL covered by the fall-through (sedans, coupes, hatchbacks).
]


# Human-readable label per size — used in the price-estimate response so
# the frontend doesn't have to translate enum values for display.
SIZE_LABEL: dict[VehicleSize, str] = {
    VehicleSize.SMALL:  "Compact / Sedan",
    VehicleSize.MEDIUM: "Mid-size SUV",
    VehicleSize.LARGE:  "Pickup / Full-size SUV",
    VehicleSize.XL:     "Van / Minivan",
}


def estimate_size_from_make_model(make: str | None, model: str | None) -> VehicleSize:
    """Approximate a VehicleSize from year/make/model when no VIN /
    body_class is available yet (Plan 24 §3 C-1).

    Uses a keyword search against the lowercased model name. The
    `make` is currently unused but kept in the signature so we can
    later disambiguate (e.g. "Ranger" — Ford pickup vs Land Rover
    Range Rover small SUV).

    Falls back to SMALL on no match — the cheapest tier, so we never
    underquote.
    """
    needle = (model or "").lower().strip()
    if not needle:
        return VehicleSize.SMALL
    for keywords, size in _MODEL_KEYWORD_TO_SIZE:
        if any(kw in needle for kw in keywords):
            return size
    return VehicleSize.SMALL


async def lookup_vin_data(vin: str) -> dict:
    """
    Decode a 17-character VIN via the NHTSA vPIC API.
    Returns a dict ready for the vehicle registration form.
    """
    vin = vin.upper().strip()
    if len(vin) != 17:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El VIN debe tener exactamente 17 caracteres.",
        )

    url = NHTSA_URL.format(vin=vin)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.TimeoutException:
            logger.error("NHTSA timeout | vin=%s", vin)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="El servicio de consulta tardó demasiado. Intenta de nuevo.",
            )
        except httpx.RequestError as exc:
            logger.error("NHTSA request error | vin=%s err=%s", vin, exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Servicio de consulta de vehículos no disponible temporalmente.",
            )

    result = resp.json()["Results"][0]
    error_code = str(result.get("ErrorCode", "1")).strip()

    if not error_code.startswith("0"):
        logger.warning("NHTSA decode failed | vin=%s code=%s", vin, error_code)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VIN no reconocido por NHTSA: {result.get('ErrorText', 'VIN inválido')}",
        )

    raw_body  = result.get("BodyClass", "") or ""
    year_str  = result.get("ModelYear", "")

    try:
        model_year = int(year_str) if year_str else None
    except ValueError:
        model_year = None

    logger.info(
        "VIN decoded | vin=%s make=%s model=%s year=%s body=%s size=%s",
        vin, result.get("Make"), result.get("Model"),
        model_year, raw_body, map_body_to_size(raw_body).value,
    )

    return {
        "make":           result.get("Make") or None,
        "model":          result.get("Model") or None,
        "year":           model_year,
        "series":         result.get("Series") or None,
        "body_class":     raw_body or None,
        "suggested_size": map_body_to_size(raw_body).value,
    }
