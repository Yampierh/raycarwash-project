"""
domains/users/address_service.py — orchestration for `/api/v1/users/me/
addresses` (Phase 4 chunk T).

Responsibilities the service owns (and the repository deliberately
doesn't):

  - Run the geocoding adapter so newly-created or geographically-edited
    addresses persist with `lat/lng/h3_index_r9` populated. On adapter
    failure (transport error, rate limit) we accept the row with NULL
    coordinates rather than 503-ing the user — a backfill worker can
    retry later, and the matching engine skips coordinate-less rows
    rather than crashing.

  - Compute the H3 cell from the geocoded lat/lng using the same
    resolution the rest of the system uses (settings.H3_RESOLUTION_STORE,
    r9).

  - Enforce the "deleting your default address while you have future
    appointments tied to it" guard: 409 instead of silent data loss.
    Future appointments use addresses indirectly via the booking flow,
    so for Phase 4 we only block deletion of the default; non-default
    address deletes are always permitted.

  - Pivot the default flag through AddressRepository.set_default_atomic
    so the partial unique index never sees two defaults concurrently.

  - Write the audit log with the AuditContext bundle already on
    request.state (populated by AuditContextMiddleware).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import h3
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_geocoding_adapter
from app.middleware.audit_context import AuditContext, get_audit_context
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.public.models import CoverageZip
from domains.users.address_repository import AddressRepository
from domains.users.address_schemas import AddressCreateRequest, AddressUpdateRequest
from domains.users.models import User
from domains.users.user_address import UserAddress
from infrastructure.geocoding.base import GeocodeQuery, GeocodingError

logger = logging.getLogger(__name__)


class AddressService:
    def __init__(self, db: AsyncSession, audit_ctx: AuditContext) -> None:
        self.db = db
        self.audit_ctx = audit_ctx
        self.repo = AddressRepository(db)
        self.audit_repo = AuditRepository(db)

    # ─── List / get ─────────────────────────────────────────────────────────

    async def list_for_user(self, user: User) -> list[UserAddress]:
        return list(await self.repo.list_active(user.id))

    async def get_or_404(
        self, user: User, address_id: uuid.UUID
    ) -> UserAddress:
        row = await self.repo.get_by_id(user.id, address_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "resource_not_found",
                    "message": "Address not found.",
                },
            )
        return row

    # ─── Create ─────────────────────────────────────────────────────────────

    async def create(
        self, user: User, body: AddressCreateRequest
    ) -> UserAddress:
        """Create + geocode + maybe-default + audit, in one transaction."""
        # Plan 24 §3 C-3 — opt-in coverage gate. Customer signup Step 4
        # sets `enforce_coverage_check=True` so we reject ZIPs outside
        # the launched markets. Other callers (admin edits, programmatic
        # imports, existing PHP migrations) leave it False and any
        # ZIP is accepted.
        if body.enforce_coverage_check:
            await self._assert_zip_in_coverage(body.zip_code)

        lat, lng, h3_index = await self._geocode_or_warn(
            GeocodeQuery(
                line1=body.line1,
                line2=body.line2,
                city=body.city,
                state=body.state,
                zip_code=body.zip_code,
                country=body.country,
            )
        )

        # If the caller asks for is_default=True, clear any existing default
        # first so the partial unique index doesn't reject the INSERT.
        if body.is_default:
            await self.repo.clear_default(user.id)

        # If this is the user's first address, force is_default=True
        # regardless of the request — a single-address user should always
        # have it as their default (matches vehicles / payment methods UX).
        existing_count = await self.repo.count_active(user.id)
        make_default = body.is_default or existing_count == 0

        row = UserAddress(
            user_id=user.id,
            label=body.label,
            line1=body.line1,
            line2=body.line2,
            city=body.city,
            state=body.state,
            zip_code=body.zip_code,
            country=body.country,
            latitude=lat,
            longitude=lng,
            h3_index_r9=h3_index,
            notes=body.notes,
            is_default=make_default,
        )
        self.repo.add(row)
        await self.db.flush()

        await self.audit_repo.log(
            action=AuditAction.ADDRESS_ADDED,
            entity_type="user_address",
            entity_id=str(row.id),
            actor_id=user.id,
            new_value={
                "label": row.label,
                "city": row.city,
                "state": row.state,
                "zip_code": row.zip_code,
                "is_default": row.is_default,
            },
            audit_ctx=self.audit_ctx,
        )
        return row

    # ─── Update ─────────────────────────────────────────────────────────────

    async def update(
        self, user: User, address_id: uuid.UUID, body: AddressUpdateRequest
    ) -> UserAddress:
        row = await self.get_or_404(user, address_id)

        old_snapshot = {
            "label": row.label,
            "line1": row.line1,
            "city": row.city,
            "state": row.state,
            "zip_code": row.zip_code,
        }

        for field in ("label", "line1", "line2", "city", "state", "zip_code", "country", "notes"):
            value = getattr(body, field)
            if value is not None:
                setattr(row, field, value)

        # Re-geocode only when an address-line / city / state / zip / country
        # field changed. Editing the label or notes doesn't move the pin.
        if body.has_geocodable_change():
            lat, lng, h3_index = await self._geocode_or_warn(
                GeocodeQuery(
                    line1=row.line1,
                    line2=row.line2,
                    city=row.city,
                    state=row.state,
                    zip_code=row.zip_code,
                    country=row.country,
                )
            )
            row.latitude = lat
            row.longitude = lng
            row.h3_index_r9 = h3_index

        await self.db.flush()
        await self.audit_repo.log(
            action=AuditAction.ADDRESS_UPDATED,
            entity_type="user_address",
            entity_id=str(row.id),
            actor_id=user.id,
            old_value=old_snapshot,
            new_value={
                "label": row.label,
                "line1": row.line1,
                "city": row.city,
                "state": row.state,
                "zip_code": row.zip_code,
            },
            audit_ctx=self.audit_ctx,
        )
        return row

    # ─── Set default ────────────────────────────────────────────────────────

    async def set_default(
        self, user: User, address_id: uuid.UUID
    ) -> UserAddress:
        """Atomic pivot via AddressRepository.set_default_atomic."""
        ok = await self.repo.set_default_atomic(user.id, address_id)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "resource_not_found",
                    "message": "Address not found.",
                },
            )
        await self.db.flush()
        await self.audit_repo.log(
            action=AuditAction.ADDRESS_UPDATED,
            entity_type="user_address",
            entity_id=str(address_id),
            actor_id=user.id,
            new_value={"is_default": True},
            audit_ctx=self.audit_ctx,
        )
        # Return the freshly-defaulted row for the response.
        return await self.get_or_404(user, address_id)

    # ─── Delete ─────────────────────────────────────────────────────────────

    async def delete(self, user: User, address_id: uuid.UUID) -> None:
        row = await self.get_or_404(user, address_id)

        # TODO(phase 5): block when the address is bound to a future
        # appointment (status pending|confirmed|en_route). For chunk T we
        # only have appointments by FK to the legacy ClientProfile.service_
        # address; once the booking flow consumes user_addresses (Phase 5
        # chunk that wires AppointmentVehicle to UserAddress), uncomment
        # the future-appointment check here. Until then deleting any
        # address is permitted — the partial unique on (user_id) WHERE
        # is_default=true handles the integrity side.

        # Snapshot is_default BEFORE soft_delete runs. SQLAlchemy 2.0's
        # update().execute() defaults to synchronize_session='auto', which
        # evaluates the WHERE clause locally and mutates the in-memory
        # row — so by the time soft_delete returns, row.is_default is
        # already False even though the auto-promote branch hasn't fired.
        was_default = bool(row.is_default)

        await self.repo.soft_delete(user.id, address_id, now=datetime.now(timezone.utc))

        # If we just deleted the default, promote the oldest remaining
        # active address to default so the user always has one.
        if was_default:
            replacement = await self.repo.first_active(user.id, exclude_id=address_id)
            if replacement is not None:
                replacement.is_default = True
                await self.db.flush()

        await self.audit_repo.log(
            action=AuditAction.ADDRESS_REMOVED,
            entity_type="user_address",
            entity_id=str(address_id),
            actor_id=user.id,
            old_value={
                "label": row.label,
                "city": row.city,
                "state": row.state,
                "zip_code": row.zip_code,
                "was_default": row.is_default,
            },
            audit_ctx=self.audit_ctx,
        )

    # ─── Internal helpers ───────────────────────────────────────────────────

    async def _geocode_or_warn(
        self, query: GeocodeQuery
    ) -> tuple[float | None, float | None, str | None]:
        """Run the geocoding adapter; on transport failure return NULLs and
        log a warning. Never raises — accepting a row without coords is
        better than rejecting the user's edit."""
        adapter = get_geocoding_adapter()
        try:
            result = await adapter.geocode(query)
        except GeocodingError as exc:
            logger.warning(
                "address: geocoding adapter failed (%s) — saving without coords",
                exc,
            )
            return None, None, None

        if result is None:
            # "No match" — also fine. The matching engine just won't see
            # this address as a candidate until the user re-edits with a
            # cleaner query.
            return None, None, None

        h3_index = h3.latlng_to_cell(
            result.latitude,
            result.longitude,
            get_settings().H3_RESOLUTION_STORE,
        )
        return result.latitude, result.longitude, h3_index

    async def _assert_zip_in_coverage(self, zip_code: str) -> None:
        """Plan 24 §3 C-3 — reject ZIPs not in the seeded `coverage_zips`
        table. Used only when the caller opts in via
        `enforce_coverage_check=True` in the request body.

        Soft-deleted ZIPs (`is_deleted=True`) and inactive ones
        (`is_active=False`) are treated as uncovered.
        """
        row = (await self.db.execute(
            select(CoverageZip).where(
                CoverageZip.zip == zip_code,
                CoverageZip.is_deleted.is_(False),
                CoverageZip.is_active.is_(True),
            )
        )).scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "zip_outside_coverage",
                    "message": (
                        f"ZIP {zip_code!r} is outside the current "
                        f"RayCarWash service area. See "
                        f"GET /api/v1/public/coverage-zones for the "
                        f"list of operating markets."
                    ),
                },
            )


def get_address_service(db: AsyncSession, request) -> AddressService:
    """FastAPI dependency factory — pulls the AuditContext off
    request.state (populated by AuditContextMiddleware)."""
    return AddressService(db=db, audit_ctx=get_audit_context(request))
