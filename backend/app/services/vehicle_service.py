# app/services/vehicle_service.py
#
# CHANGES vs previous version:
#
#   [BUG FIXED] get_size_from_body_class duplicated map_body_to_size from
#   vehicle_lookup.py with inconsistent rules (van → XL here, van → LARGE there).
#   The function was also imported in vehicle_router.py but never called —
#   pure dead code causing confusion.
#
#   Fix: this module now re-exports map_body_to_size from vehicle_lookup.py.
#   There is one canonical implementation, one source of truth.
#   vehicle_router.py only needs to import from vehicle_lookup.py.
#   This file is kept for future vehicle-specific business logic.

from __future__ import annotations

# Re-export the canonical mapping so any code that imported from this
# module continues to work without changes.
from app.services.vehicle_lookup import map_body_to_size as get_size_from_body_class

__all__ = ["get_size_from_body_class"]