# app/services/vehicle_lookup.py
#
# NHTSA vPIC API integration — VIN decode.
#
# BUGS FIXED vs previous version:
#
#   [BUG-1] NHTSA ErrorCode strict equality crash:
#     OLD: result.get("ErrorCode") != "0"
#     The NHTSA API returns strings like "0 - VIN decoded clean; error code 0"
#     NOT a bare "0". Strict == "0" was rejecting all real VINs as errors.
#     FIX: str(error_code).startswith("0") handles all success variants.
#
#   [BUG-2] Duplicated + inconsistent map_body_to_size:
#     vehicle_service.py defined get_size_from_body_class returning XL for vans.
#     vehicle_lookup.py defined map_body_to_size returning LARGE for vans.
#     The router called map_body_to_size but imported both — dead code + wrong prices.
#     FIX: This file is the canonical source. XL for vans (correct per pricing matrix).
#          vehicle_service.py now re-exports from here.
#
# DEPENDENCY: httpx — add `httpx>=0.27.0` to requirements.txt if not present.

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from app.models.models import VehicleSize

logger = logging.getLogger(__name__)

NHTSA_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{vin}?format=json"


# ── Canonical size mapping (single source of truth) ──────────────── #
#
# Never define this mapping in two places.
# Import map_body_to_size everywhere that needs it.
#
# Pricing alignment:
#   SMALL  (×1.0) — Sedan, Coupe, Hatchback, Convertible
#   MEDIUM (×1.2) — SUV, Crossover, CUV
#   LARGE  (×1.5) — Pickup truck (F-150, Sierra, Tundra)
#   XL     (×2.0) — Van, Minivan, Sprinter  ← FIX: was LARGE in old version

def map_body_to_size(body_class: str | None) -> VehicleSize:
    """
    Map an NHTSA BodyClass string to a VehicleSize pricing tier.

    Args:
        body_class: Raw text from NHTSA or user input.
                    Examples: "Pickup", "Sport Utility Vehicle (SUV/CUV)", "Van"
    Returns:
        VehicleSize enum value.
    """
    bc = (body_class or "").lower().strip()

    if "pickup" in bc:
        return VehicleSize.LARGE

    if "utility vehicle" in bc or "suv" in bc or "crossover" in bc or "cuv" in bc:
        return VehicleSize.MEDIUM

    if "van" in bc or "minivan" in bc:
        # XL is correct here — vans (Sprinter, Transit) carry the highest multiplier.
        # The old vehicle_lookup.py incorrectly returned LARGE.
        return VehicleSize.XL

    return VehicleSize.SMALL


# ── NHTSA vPIC lookup ─────────────────────────────────────────────── #

async def lookup_vin_data(vin: str) -> dict:
    """
    Decode a 17-character VIN via the free NHTSA vPIC API.

    Returns a cleaned dict ready for the frontend to pre-fill the
    vehicle registration form. The `suggested_size` field shows the
    pricing tier the backend will apply.

    Raises:
        HTTPException 400: VIN length != 17.
        HTTPException 404: NHTSA could not decode the VIN.
        HTTPException 503: NHTSA API is unreachable or timed out.
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

    # FIX: NHTSA success codes start with "0" but are rarely just "0".
    # Common success string: "0 - VIN decoded clean; error code 0 for position 1"
    # Old code: != "0"  →  failed for every real VIN
    # New code: not startswith("0")  →  correctly accepts all success variants
    if not error_code.startswith("0"):
        logger.warning("NHTSA decode failed | vin=%s code=%s", vin, error_code)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VIN no reconocido por NHTSA: {result.get('ErrorText', 'VIN inválido')}",
        )

    raw_body   = result.get("BodyClass", "") or ""
    year_str   = result.get("ModelYear", "")

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