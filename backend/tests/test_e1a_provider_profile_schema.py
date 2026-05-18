"""
tests/test_e1a_provider_profile_schema.py — Integration plan E1 chunk A.

Schema-level invariants that the multi-profile refactor depends on:

  * provider_type defaults to "detailer" so existing rows backfill safely
  * is_active defaults to True (mirrors is_accepting_bookings)
  * composite unique (user_id, provider_type) lets a user hold one
    DETAILER + one MECHANIC profile
  * composite unique rejects a second profile of the same type

E1.A keeps the relationship 1:1 on User; the relationship flip happens
in E1.B. The composite constraint is in place so E1.B can extend
without a follow-up migration.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from domains.providers.models import ProviderProfile, ProviderType
from domains.users.models import User


async def _make_user(db: AsyncSession, email: str) -> User:
    """Insert a bare User row so the FK on provider_profiles resolves."""
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name="E1A Tester",
        password_hash="x",
    )
    db.add(user)
    await db.flush()
    return user


# ─── default values ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_provider_type_defaults_to_detailer(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1a-default@test.com")
    profile = ProviderProfile(user_id=user.id)
    db_session.add(profile)
    await db_session.flush()
    await db_session.refresh(profile)

    assert profile.provider_type == ProviderType.DETAILER.value
    assert profile.is_active is True


@pytest.mark.asyncio
async def test_provider_type_accepts_mechanic(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1a-mechanic@test.com")
    profile = ProviderProfile(
        user_id=user.id, provider_type=ProviderType.MECHANIC.value,
    )
    db_session.add(profile)
    await db_session.flush()
    await db_session.refresh(profile)

    assert profile.provider_type == ProviderType.MECHANIC.value


# ─── composite unique (user_id, provider_type) ───────────────────────────────


@pytest.mark.asyncio
async def test_user_can_hold_detailer_and_mechanic_profiles(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1a-dual@test.com")
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
    ))
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.MECHANIC.value,
    ))
    # Both inserts must succeed — composite unique allows DETAILER + MECHANIC.
    await db_session.flush()

    rows = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.user_id == user.id)
    )).scalars().all()
    assert len(rows) == 2
    types = {p.provider_type for p in rows}
    assert types == {
        ProviderType.DETAILER.value,
        ProviderType.MECHANIC.value,
    }


@pytest.mark.asyncio
async def test_user_cannot_hold_two_profiles_of_same_type(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1a-dup@test.com")
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
    ))
    await db_session.flush()

    # Second DETAILER profile must violate uq_provider_profiles_user_type.
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
    ))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


# ─── relationship is still 1:1 in E1.A ───────────────────────────────────────


@pytest.mark.asyncio
async def test_user_provider_profile_relationship_returns_first(
    db_session: AsyncSession,
) -> None:
    """
    User.provider_profile is intentionally still uselist=False until E1.B.
    With composite unique allowing two rows per user, the existing 1:1
    relationship resolves to the row PostgreSQL returns first — fine for
    today since activation flows only create DETAILER. E1.B introduces
    `provider_profiles` (list) and the `provider_profile_for(type)`
    helper.
    """
    user = await _make_user(db_session, "e1a-rel@test.com")
    db_session.add(ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
        bio="detailer-bio",
    ))
    await db_session.flush()

    fetched = (await db_session.execute(
        select(User).where(User.id == user.id)
    )).scalar_one()
    assert fetched.provider_profile is not None
    assert fetched.provider_profile.provider_type == ProviderType.DETAILER.value
    assert fetched.provider_profile.bio == "detailer-bio"
