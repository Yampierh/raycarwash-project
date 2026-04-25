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
