"""
domains/users/hub_service.py — Composes the Profile Hub response (ADR-002b).

The service stays thin: each block has a `_build_<token>_block()` method
that runs only when the matching token is in `IncludeSpec.effective`.
Sensitive blocks (`security`, `sessions`) are skipped silently when
`?on_step_up=skip` is passed and the caller is not in a recent step-up
window — the router records that in `meta.skipped_due_to_step_up`.

Cross-domain reads use existing repositories where they exist (auth's
RefreshTokenRepository, the future PaymentMethodRepository, etc.).
Phase 1 ships the blocks that work today against the columns added by
m_002..m_004. Blocks for resources not yet implemented (vehicles photo URLs,
payment_methods sync, addresses, favorites, notifications, sessions
detail rows) return empty lists in the meantime — frontend can call those
endpoints when they ship in later phases and the Hub layout doesn't need
to change.
"""
from __future__ import annotations

import logging
from datetime import datetime
from datetime import timezone as _tz
from typing import Awaitable, Callable

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_public_storage
from app.core.step_up import is_step_up_recent
from domains.auth.models import (
    RefreshToken,
    UserLoginHistory,
    WebAuthnCredential,
)
from domains.users.hub_schemas import (
    AddressSummary,
    FavoriteProviderSummary,
    HubResponse,
    NotificationsBlock,
    PaymentMethodSummary,
    PreferencesBlock,
    ProfileBlock,
    ProviderBlock,
    SecurityBlock,
    SessionItem,
    StatsBlock,
    UserCoreBlock,
    VehicleSummary,
    VerificationBadgesBlock,
)
from domains.users.include_spec import IncludeSpec, SENSITIVE_TOKENS
from domains.users.models import ClientProfile, User

logger = logging.getLogger(__name__)


class ProfileHubService:
    """
    Orchestrates the Profile Hub response. Each `_build_*` method is keyed by
    a token in `IncludeSpec`. The service NEVER raises for missing data —
    fields default to empty lists / None / 0 — so a half-populated user
    still gets a coherent Hub.
    """

    def __init__(self, db: AsyncSession, request: Request) -> None:
        self.db = db
        self.request = request

    # ────── Public entry point ──────────────────────────────────────────────

    async def build(
        self,
        user: User,
        spec: IncludeSpec,
        *,
        on_step_up_skip: bool = False,
    ) -> tuple[HubResponse, frozenset[str], frozenset[str]]:
        """
        Build a `HubResponse` honoring the include spec.

        Returns:
            (response, populated_tokens, skipped_due_to_step_up)
            - populated_tokens — the set of include tokens that landed in
              the response. Echoed into `meta.includes`.
            - skipped_due_to_step_up — sensitive tokens (security, sessions)
              that were omitted because the caller has no recent step-up
              AND `on_step_up_skip=True`. The router uses this to populate
              `meta.skipped_due_to_step_up`.

        When the caller has no recent step-up and `on_step_up_skip=False`,
        the router raises StepUpRequiredError BEFORE calling us — we never
        see that case here.
        """
        # `user` and `verification_badges` are always present.
        hub = HubResponse(
            user=self._build_user_core(user),
            verification_badges=self._build_verification_badges(user),
        )

        populated: set[str] = set()
        skipped: set[str] = set()

        # Sensitive tokens: maybe-skip when not in step-up window.
        sensitive_in_spec = spec.effective & SENSITIVE_TOKENS
        sensitive_allowed: set[str] = set()
        if sensitive_in_spec:
            step_up_ok = await is_step_up_recent(self.request, user)
            if step_up_ok:
                sensitive_allowed = set(sensitive_in_spec)
            elif on_step_up_skip:
                skipped = set(sensitive_in_spec)
            # When step_up_ok is False AND on_step_up_skip is False, the
            # router has already raised StepUpRequiredError — we wouldn't be
            # in this branch.

        # Dispatch table — keyed by token, value is the builder.
        builders: dict[str, Callable[[User], Awaitable[None] | None]] = {
            "profile":         lambda u: self._set(hub, "profile",         self._build_profile_block(u)),
            "stats":           lambda u: self._await_set(hub, "stats",     self._build_stats_block(u)),
            "preferences":     lambda u: self._set(hub, "preferences",     self._build_preferences_block(u)),
            "notifications":   lambda u: self._set(hub, "notifications",   self._build_notifications_block(u)),
            "provider":        lambda u: self._set(hub, "provider",        self._build_provider_block(u)),
            "vehicles":        lambda u: self._await_set(hub, "vehicles",  self._build_vehicles_block(u)),
            "addresses":       lambda u: self._await_set(hub, "addresses", self._build_addresses_block(u)),
            "payment_methods": lambda u: self._await_set(hub, "payment_methods", self._build_payment_methods_block(u)),
            "favorites":       lambda u: self._await_set(hub, "favorites", self._build_favorites_block(u)),
            "security":        lambda u: self._await_set(hub, "security",  self._build_security_block(u)),
            "sessions":        lambda u: self._await_set(hub, "sessions",  self._build_sessions_block(u)),
        }

        for token in spec.effective:
            if token in SENSITIVE_TOKENS and token not in sensitive_allowed:
                continue
            builder = builders.get(token)
            if builder is None:
                logger.warning("hub: unknown token reached builder dispatch: %s", token)
                continue
            result = builder(user)
            if result is not None and hasattr(result, "__await__"):
                await result
            populated.add(token)

        return hub, frozenset(populated), frozenset(skipped)

    # ────── Tiny helpers for the dispatch table ─────────────────────────────

    @staticmethod
    def _set(hub: HubResponse, attr: str, value) -> None:
        setattr(hub, attr, value)

    @staticmethod
    async def _await_set(hub: HubResponse, attr: str, coro) -> None:
        setattr(hub, attr, await coro)

    # ────── Always-on blocks ────────────────────────────────────────────────

    def _build_user_core(self, user: User) -> UserCoreBlock:
        # `available_roles` comes from User.user_roles (selectin-loaded).
        roles = [ur.role.name for ur in (user.user_roles or [])]
        active = user.active_role
        if active is None and roles:
            # Legacy single-role users: surface their only role as active.
            active = roles[0]
        return UserCoreBlock(
            id=user.id,
            email=user.email,
            email_verified=user.is_verified,
            phone=user.phone_number,
            phone_verified=user.phone_number is not None,
            role=active,
            available_roles=roles,
            created_at=user.created_at,
        )

    def _build_verification_badges(self, user: User) -> VerificationBadgesBlock:
        pp = user.provider_profile
        return VerificationBadgesBlock(
            email=user.is_verified,
            phone=user.phone_number is not None,
            identity=bool(pp and pp.verification_status == "approved"),
            background_check=bool(pp and pp.background_check_consent),
        )

    # ────── Profile + Stats + Preferences ───────────────────────────────────

    def _build_profile_block(self, user: User) -> ProfileBlock:
        first, last = _split_full_name(user.full_name)
        return ProfileBlock(
            first_name=first,
            last_name=last,
            full_name=user.full_name,
            pronouns=user.pronouns,
            avatar_url=self._sign_url(user.avatar_s3_key),
            cover_url=self._sign_url(user.cover_s3_key),
            language=user.preferred_language or "en",
            timezone=user.preferred_timezone or "America/Indiana/Indianapolis",
        )

    async def _build_stats_block(self, user: User) -> StatsBlock:
        cp = user.client_profile
        member_since = user.created_at.date() if user.created_at else None
        # Vehicles count is cheap (small per-user FK table). Favorites table
        # doesn't exist yet (Phase 4) — return 0.
        vehicles_total = await self._count_vehicles(user.id)
        return StatsBlock(
            # TODO(phase 9 m_020): total_appointments_count / total_spent_cents
            # are denormalized fields maintained by a PostgreSQL trigger that
            # fires on appointments status=completed and payment_ledger CAPTURE
            # entries. Phase 1 reads them as 0 for pre-trigger data.
            total_bookings=(cp.total_appointments_count if cp else 0),
            total_spent_cents=(cp.total_spent_cents if cp else 0),
            # TODO(phase 4 m_008): wire to ClientFavorite (most-used or
            # explicit-pinned provider). Today there is no concept of a
            # favorite_provider on the schema — Phase 4 introduces it.
            favorite_provider_id=None,
            vehicles_total=vehicles_total,
            # TODO(phase 4 m_008): count from ClientFavorite once the table
            # lands.
            favorites_total=0,
            member_since=member_since,
        )

    def _build_preferences_block(self, user: User) -> PreferencesBlock | None:
        cp = user.client_profile
        if cp is None:
            return None
        return PreferencesBlock(
            default_vehicle_id=cp.default_vehicle_id,
            default_address_id=cp.default_address_id,
            marketing_opt_in=cp.marketing_email_opt_in,
            frequency_preference=cp.frequency_preference,
        )

    def _build_notifications_block(self, user: User) -> NotificationsBlock:
        # TODO(phase 7 m_014): read from NotificationPreference table (channel ×
        # topic matrix + quiet hours). The frontend already renders the empty
        # placeholder so wiring the real source is a drop-in replacement.
        return NotificationsBlock(preferences={})

    # ────── Provider block ──────────────────────────────────────────────────

    def _build_provider_block(self, user: User) -> ProviderBlock | None:
        pp = user.provider_profile
        if pp is None:
            return None
        rating = float(pp.average_rating) if pp.average_rating is not None else None
        return ProviderBlock(
            business_name=pp.business_name,
            display_name=pp.display_name,
            tagline=pp.tagline,
            bio=pp.bio,
            verification_status=pp.verification_status or "not_submitted",
            rating=rating,
            total_jobs=pp.total_services_completed or 0,
            is_accepting_bookings=pp.is_accepting_bookings,
        )

    # ────── Lists landing in later phases ───────────────────────────────────

    async def _build_vehicles_block(self, user: User) -> list[VehicleSummary]:
        # Vehicle table exists; photo URLs and is_default land in Phase 4.
        from domains.vehicles.models import Vehicle  # local import to avoid cycle

        stmt = (
            select(Vehicle)
            .where(Vehicle.owner_id == user.id, Vehicle.is_deleted.is_(False))
            .order_by(Vehicle.created_at.asc())
        )
        rows = (await self.db.scalars(stmt)).all()
        default_id = user.client_profile.default_vehicle_id if user.client_profile else None
        return [
            VehicleSummary(
                id=v.id,
                make=v.make,
                model=v.model,
                year=v.year,
                color=v.color,
                license_plate=v.license_plate,
                photo_url=None,  # Phase 4 (VehiclePhoto)
                is_default=(v.id == default_id),
            )
            for v in rows
        ]

    async def _build_addresses_block(self, user: User) -> list[AddressSummary]:
        from domains.users.address_repository import AddressRepository

        rows = await AddressRepository(self.db).list_active(user.id)
        return [
            AddressSummary(
                id=r.id,
                label=r.label,
                line1=r.line1,
                city=r.city,
                state=r.state,
                zip_code=r.zip_code,
                is_default=r.is_default,
            )
            for r in rows
        ]

    async def _build_payment_methods_block(self, user: User) -> list[PaymentMethodSummary]:
        # TODO(phase 4 m_007): replace with a SELECT against payment_methods
        # (mirrored from Stripe via webhook). Currency / brand / last4 already
        # in the response schema.
        return []

    async def _build_favorites_block(self, user: User) -> list[FavoriteProviderSummary]:
        # TODO(phase 4 m_008): replace with a JOIN client_favorites →
        # provider_profiles → users to return display_name + avatar_url.
        return []

    # ────── Security + sessions (step-up gated) ─────────────────────────────

    async def _build_security_block(self, user: User) -> SecurityBlock:
        passkeys_count = await self.db.scalar(
            select(func.count())
            .select_from(WebAuthnCredential)
            .where(WebAuthnCredential.user_id == user.id)
        ) or 0
        sessions_count = await self.db.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
            )
        ) or 0
        last_login_at = await self.db.scalar(
            select(func.max(UserLoginHistory.login_at))
            .where(
                UserLoginHistory.user_id == user.id,
                UserLoginHistory.was_successful.is_(True),
            )
        )
        recent_failed = await self.db.scalar(
            select(func.count())
            .select_from(UserLoginHistory)
            .where(
                UserLoginHistory.user_id == user.id,
                UserLoginHistory.was_successful.is_(False),
            )
        ) or 0
        return SecurityBlock(
            has_password=bool(user.password_hash),
            # TODO(phase 3 m_005b): read from TotpCredential.enabled once the
            # table lands. Today every account reports False because there's
            # no TOTP storage.
            two_factor_enabled=False,
            passkeys_count=int(passkeys_count),
            # TODO(phase 3): derive from audit_log
            # WHERE action=PASSWORD_CHANGED, actor=user, ORDER BY created_at
            # DESC LIMIT 1. Requires the password-change endpoint to actually
            # log that action (Phase 3 chunk wiring).
            last_password_change=None,
            last_login_at=last_login_at,
            step_up_required=False,
            active_sessions_count=int(sessions_count),
            recent_failed_attempts=int(recent_failed),
        )

    async def _build_sessions_block(self, user: User) -> list[SessionItem]:
        # One row per active RefreshToken family, enriched with the most
        # recent successful UserLoginHistory entry whose family matches.
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked.is_(False),
            )
            .order_by(RefreshToken.created_at.desc())
        )
        tokens = (await self.db.scalars(stmt)).all()
        items: list[SessionItem] = []
        for t in tokens:
            login = await self.db.scalar(
                select(UserLoginHistory)
                .where(
                    UserLoginHistory.user_id == user.id,
                    UserLoginHistory.refresh_token_family_id == t.family_id,
                    UserLoginHistory.was_successful.is_(True),
                )
                .order_by(UserLoginHistory.login_at.desc())
                .limit(1)
            )
            items.append(SessionItem(
                id=t.id,
                device_name=getattr(login, "device_name", None),
                user_agent=getattr(login, "user_agent", None),
                ip_address=getattr(login, "ip_address", None),
                ip_location=getattr(login, "ip_location", None),
                # TODO(phase 3): determine is_current by matching t.family_id
                # against the refresh token used to mint the request's access
                # token. Needs AuthService to surface the family on
                # request.state. Today every session reports False, which is
                # safe but means the frontend "this device" indicator is
                # always missing.
                is_current=False,
                created_at=t.created_at,
                last_seen_at=getattr(login, "login_at", None),
            ))
        return items

    # ────── Internal utilities ──────────────────────────────────────────────

    async def _count_vehicles(self, user_id) -> int:
        from domains.vehicles.models import Vehicle  # local import to avoid cycle

        count = await self.db.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(Vehicle.owner_id == user_id, Vehicle.is_deleted.is_(False))
        )
        return int(count or 0)

    def _sign_url(self, s3_key: str | None) -> str | None:
        """
        Generate a download URL for an S3 key. In dev we know
        LocalStorageAdapter serves files under /storage/{bucket}/{key}, so
        we build the URL synchronously without awaiting the async signer.

        TODO(prod) — when S3StorageAdapter ships, this needs to call
        `await adapter.generate_download_url(s3_key, ttl_seconds=86_400)`
        instead of constructing the path manually. Today the sync path
        works because LocalStorageAdapter ignores `ttl_seconds` and
        returns the same /storage/<bucket>/<key> regardless. The async
        version requires either (a) refactoring `_build_profile_block` to
        be async too, or (b) caching pre-signed URLs in the hub cache
        layer. See plan §9 (Redis caching) — the cache key already
        includes `token_version` which invalidates when the key rotates.
        """
        if not s3_key:
            return None
        try:
            adapter = get_public_storage()
            return f"/storage/{adapter.bucket}/{s3_key}"
        except Exception as exc:
            logger.warning("hub: failed to build URL for %s: %s", s3_key, exc)
            return None

    async def update_profile_fields(
        self,
        user: User,
        *,
        first_name: str | None,
        last_name: str | None,
        pronouns: str | None,
        language: str | None,
        timezone_name: str | None,
    ) -> User:
        """
        Apply a PATCH /users/me payload to the User row. Only profile-block
        fields are mutable here; email/phone go through their own flows.
        full_name is stored as a single column — first/last are derived in
        the Profile block. When the caller supplies first/last separately
        we recompose full_name as "First Last".

        `timezone_name` is the IANA tz string; named with a suffix to avoid
        shadowing the `datetime.timezone` import.
        """
        if first_name is not None or last_name is not None:
            current_first, current_last = _split_full_name(user.full_name)
            new_first = first_name if first_name is not None else current_first or ""
            new_last = last_name if last_name is not None else current_last or ""
            full = (new_first + " " + new_last).strip()
            if full:
                user.full_name = full

        if pronouns is not None:
            user.pronouns = pronouns
        if language is not None:
            user.preferred_language = language
        if timezone_name is not None:
            user.preferred_timezone = timezone_name

        user.last_active_at = datetime.now(_tz.utc)
        await self.db.flush()
        return user


# ─── helpers ─────────────────────────────────────────────────────────────────


def _split_full_name(full_name: str | None) -> tuple[str | None, str | None]:
    """Split "First Middle Last" into ("First", "Middle Last"). Best-effort."""
    if not full_name:
        return None, None
    parts = full_name.strip().split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]
