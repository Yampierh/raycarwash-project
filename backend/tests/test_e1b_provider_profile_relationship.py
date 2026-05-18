"""
tests/test_e1b_provider_profile_relationship.py — Integration plan E1 chunk B.

The 1:1 mapped relationship `User.provider_profile` is replaced by a 1:N
`User.provider_profiles` (list, selectin-loaded). A back-compat
`@property provider_profile` returns the DETAILER row for legacy callers
that haven't migrated to `provider_profile_for(type)` yet.

These tests pin down:
  * provider_profiles loads as a list of all non-deleted profiles
  * provider_profile_for(DETAILER) and (MECHANIC) return the right row
  * back-compat property still returns the DETAILER profile
  * a soft-deleted row is excluded from both helpers
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.providers.models import ProviderProfile, ProviderType
from domains.users.models import User


async def _make_user(db: AsyncSession, email: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name="E1B Tester",
        password_hash="x",
    )
    db.add(user)
    await db.flush()
    return user


async def _reload_user(db: AsyncSession, user_id: uuid.UUID) -> User:
    """
    Re-fetch the User row via a fresh `select()` so the selectin-loaded
    provider_profiles relationship populates without triggering a lazy
    load (which would raise MissingGreenlet outside the original query).
    """
    return (await db.execute(
        select(User).where(User.id == user_id)
    )).scalar_one()


# ─── provider_profiles list ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_provider_profiles_loads_both_verticals(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1b-both@test.com")
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
        bio="detail-bio",
    ))
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.MECHANIC.value,
        bio="mech-bio",
    ))
    await db_session.flush()

    fetched = await _reload_user(db_session, user.id)
    assert len(fetched.provider_profiles) == 2
    bios = {p.bio for p in fetched.provider_profiles}
    assert bios == {"detail-bio", "mech-bio"}


# ─── provider_profile_for(type) helper ───────────────────────────────────────


@pytest.mark.asyncio
async def test_provider_profile_for_returns_specific_type(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1b-for@test.com")
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
        bio="detail-bio",
    ))
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.MECHANIC.value,
        bio="mech-bio",
    ))
    await db_session.flush()
    user = await _reload_user(db_session, user.id)

    detailer = user.provider_profile_for(ProviderType.DETAILER)
    mechanic = user.provider_profile_for(ProviderType.MECHANIC)
    assert detailer is not None and detailer.bio == "detail-bio"
    assert mechanic is not None and mechanic.bio == "mech-bio"


@pytest.mark.asyncio
async def test_provider_profile_for_accepts_string_value(
    db_session: AsyncSession,
) -> None:
    """Calling helper with the raw string ('detailer'/'mechanic') is supported
    so call-sites that already carry the string from a JWT or DB row don't
    need to import the enum."""
    user = await _make_user(db_session, "e1b-str@test.com")
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.MECHANIC.value,
    ))
    await db_session.flush()
    user = await _reload_user(db_session, user.id)

    assert user.provider_profile_for("mechanic") is not None
    assert user.provider_profile_for("detailer") is None


@pytest.mark.asyncio
async def test_provider_profile_for_returns_none_when_missing(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1b-none@test.com")
    user = await _reload_user(db_session, user.id)
    assert user.provider_profile_for(ProviderType.DETAILER) is None
    assert user.provider_profile_for(ProviderType.MECHANIC) is None


# ─── soft-delete is excluded ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_provider_profile_for_skips_soft_deleted(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1b-soft@test.com")
    pp = ProviderProfile(
        user_id=user.id, provider_type=ProviderType.MECHANIC.value,
    )
    db_session.add(pp)
    await db_session.flush()
    pp.is_deleted = True
    await db_session.flush()
    user = await _reload_user(db_session, user.id)

    assert user.provider_profile_for(ProviderType.MECHANIC) is None


# ─── back-compat property ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_back_compat_property_returns_detailer(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1b-bc@test.com")
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.MECHANIC.value,
        bio="mech-bio",
    ))
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
        bio="detail-bio",
    ))
    await db_session.flush()
    user = await _reload_user(db_session, user.id)

    # provider_profile (legacy) MUST resolve to the detailer row even
    # when a mechanic row exists.
    assert user.provider_profile is not None
    assert user.provider_profile.provider_type == ProviderType.DETAILER.value
    assert user.provider_profile.bio == "detail-bio"


@pytest.mark.asyncio
async def test_back_compat_property_none_when_only_mechanic(
    db_session: AsyncSession,
) -> None:
    """A user that holds only a MECHANIC profile must NOT trip
    `user.provider_profile` callers into thinking they have a detailer
    profile. This is the safety guarantee that lets us keep the shim."""
    user = await _make_user(db_session, "e1b-mech-only@test.com")
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.MECHANIC.value,
    ))
    await db_session.flush()
    user = await _reload_user(db_session, user.id)

    assert user.provider_profile is None
