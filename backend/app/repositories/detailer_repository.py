# app/repositories/detailer_repository.py  —  Sprint 4
#
# ADDITIONS:
#   - list_available()   — paginated discovery with optional Haversine geo-filter
#   - update_profile()   — PATCH semantics (only non-None fields updated)
#   - create_profile_for_user() — same as create_profile but logs clearly

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ProviderProfile, User, Role, UserRoleAssociation


# ------------------------------------------------------------------ #
#  Haversine helper                                                   #
# ------------------------------------------------------------------ #

def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Great-circle distance in miles between two WGS-84 coordinate pairs.

    Formula: Haversine (numerically stable for small distances).
    Earth radius: 3 958.8 statute miles.
    """
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


class ProviderRepository:

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ---------------------------------------------------------------- #
    #  Read                                                             #
    # ---------------------------------------------------------------- #

    async def get_profile(self, user_id: uuid.UUID) -> ProviderProfile | None:
        stmt = select(ProviderProfile).where(
            ProviderProfile.user_id == user_id,
            ProviderProfile.is_deleted.is_(False),
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_working_hours(self, user_id: uuid.UUID) -> dict | None:
        """Return the JSONB working_hours dict for a detailer."""
        profile = await self.get_profile(user_id)
        return profile.working_hours if profile else None

    # ---------------------------------------------------------------- #
    #  Discovery  (Sprint 4)                                            #
    # ---------------------------------------------------------------- #

    async def list_available(
        self,
        lat: float | None = None,
        lng: float | None = None,
        radius_miles: float = 25.0,
        min_rating: float | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Return a paginated list of available detailers, optionally filtered
        by proximity to (lat, lng) within radius_miles.

        ALGORITHM:
          1. JOIN users + provider_profiles.
          2. Filter: active DETAILER, is_accepting_bookings, not deleted.
          3. Optional: min_rating filter.
          4. Optional bounding-box pre-filter (cheap SQL) before Haversine.
          5. Python-side Haversine exact filter + distance annotation.
          6. Sort: by distance asc if geo-query, else by rating desc.
          7. Manual pagination on the filtered+sorted list.

        Returns:
          (rows, total_count)
          Each row: {"user": User, "profile": ProviderProfile, "distance_miles": float | None}

        NOTE: For production scale (>10k detailers), replace with PostGIS
        ST_DWithin() + ST_Distance() for O(log n) index-backed geo queries.
        """
        filters = [
            Role.name == "detailer",
            User.is_active.is_(True),
            User.is_deleted.is_(False),
            ProviderProfile.is_deleted.is_(False),
            ProviderProfile.is_accepting_bookings.is_(True),
        ]

        if min_rating is not None:
            filters.append(ProviderProfile.average_rating >= min_rating)

        # Bounding-box pre-filter — cuts down rows before expensive Haversine.
        # 1° latitude ≈ 69 miles; longitude degree shrinks by cos(lat).
        if lat is not None and lng is not None:
            lat_delta = radius_miles / 69.0
            lng_delta = radius_miles / max(
                0.001, 69.0 * math.cos(math.radians(lat))
            )
            filters.extend([
                ProviderProfile.current_lat.isnot(None),
                ProviderProfile.current_lng.isnot(None),
                ProviderProfile.current_lat.between(lat - lat_delta, lat + lat_delta),
                ProviderProfile.current_lng.between(lng - lng_delta, lng + lng_delta),
            ])

        stmt = (
            select(User, ProviderProfile)
            .join(UserRoleAssociation, UserRoleAssociation.user_id == User.id)
            .join(Role, Role.id == UserRoleAssociation.role_id)
            .join(ProviderProfile, ProviderProfile.user_id == User.id)
            .where(and_(*filters))
        )

        result = await self._db.execute(stmt)
        rows = result.all()

        enriched: list[dict[str, Any]] = []
        for user, profile in rows:
            distance: float | None = None
            if lat is not None and lng is not None:
                if profile.current_lat is not None and profile.current_lng is not None:
                    distance = _haversine_miles(
                        lat, lng,
                        float(profile.current_lat), float(profile.current_lng),
                    )
                    # Exact filter — bounding box may include corners outside radius
                    if distance > radius_miles:
                        continue
                else:
                    # Detailer has no location yet — skip in geo-filtered results
                    continue

            enriched.append({
                "user": user,
                "profile": profile,
                "distance_miles": distance,
            })

        # Sort
        if lat is not None and lng is not None:
            enriched.sort(key=lambda x: x["distance_miles"] or float("inf"))
        else:
            enriched.sort(
                key=lambda x: float(x["profile"].average_rating or 0),
                reverse=True,
            )

        total = len(enriched)
        offset = (page - 1) * page_size
        return enriched[offset: offset + page_size], total

    # ---------------------------------------------------------------- #
    #  Write                                                            #
    # ---------------------------------------------------------------- #

    async def create_profile(self, profile: ProviderProfile) -> ProviderProfile:
        self._db.add(profile)
        await self._db.flush()
        await self._db.refresh(profile)
        return profile

    async def update_profile(
        self,
        user_id: uuid.UUID,
        fields: dict[str, Any],
    ) -> ProviderProfile | None:
        """
        PATCH semantics: only update columns present in `fields`.
        Returns the updated profile or None if it doesn't exist.

        Caller should pass only non-None values from the request payload.
        `fields` must not contain user_id or id (immutable identity columns).
        """
        if not fields:
            return await self.get_profile(user_id)

        fields["updated_at"] = datetime.now(timezone.utc)

        await self._db.execute(
            update(ProviderProfile)
            .where(
                ProviderProfile.user_id == user_id,
                ProviderProfile.is_deleted.is_(False),
            )
            .values(**fields)
        )
        await self._db.flush()
        return await self.get_profile(user_id)

    async def update_location(
        self,
        user_id: uuid.UUID,
        lat: float,
        lng: float,
    ) -> None:
        """
        Update only the three location columns — no full ORM object load needed.

        Using a targeted UPDATE is more efficient than fetching the full User
        object, modifying it, and flushing. For a location-tracking endpoint
        that may be called every 30 seconds per active detailer, this matters.
        """
        # Fix: current_lat/lng/last_location_update live on ProviderProfile, not User
        await self._db.execute(
            update(ProviderProfile)
            .where(ProviderProfile.user_id == user_id)
            .values(
                current_lat=lat,
                current_lng=lng,
                last_location_update=datetime.now(timezone.utc),
            )
        )
        await self._db.flush()
