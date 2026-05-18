"""
tests/test_e1e_is_accepting_bookings_property.py — Integration plan E1 chunk E.

The column `provider_profiles.is_accepting_bookings` was dropped in
`m_017`. The legacy attribute name survives as a Python `@property`
on ProviderProfile that forwards reads and writes to `is_active`,
so:
  * existing callers (Phase 5 service, schemas) keep using the legacy
    name without code churn;
  * mobile/web/marketing JSON contracts (which serialize the legacy
    field name) keep returning the same boolean;
  * a single canonical column (`is_active`) backs both names.

These tests pin the property contract end-to-end.
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
        full_name="E1E Tester",
        password_hash="x",
    )
    db.add(user)
    await db.flush()
    return user


# ─── Schema check — column is gone ───────────────────────────────────────────


def test_provider_profile_no_longer_has_is_accepting_bookings_column() -> None:
    """The ORM column declaration was removed in E1.E. The attribute
    survives only as a Python @property."""
    cols = {c.name for c in ProviderProfile.__table__.columns}
    assert "is_accepting_bookings" not in cols
    assert "is_active" in cols


# ─── Reads via @property ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_is_accepting_bookings_mirrors_is_active_when_true(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1e-true@test.com")
    pp = ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
        is_active=True,
    )
    db_session.add(pp)
    await db_session.flush()

    fetched = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.id == pp.id)
    )).scalar_one()
    assert fetched.is_active is True
    assert fetched.is_accepting_bookings is True


@pytest.mark.asyncio
async def test_is_accepting_bookings_mirrors_is_active_when_false(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1e-false@test.com")
    pp = ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
        is_active=False,
    )
    db_session.add(pp)
    await db_session.flush()

    fetched = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.id == pp.id)
    )).scalar_one()
    assert fetched.is_active is False
    assert fetched.is_accepting_bookings is False


# ─── Writes via @property.setter ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_setting_is_accepting_bookings_persists_to_is_active(
    db_session: AsyncSession,
) -> None:
    """Legacy code that does `pp.is_accepting_bookings = True` must end
    up with is_active=True on the DB row."""
    user = await _make_user(db_session, "e1e-set@test.com")
    pp = ProviderProfile(
        user_id=user.id, provider_type=ProviderType.DETAILER.value,
        is_active=False,
    )
    db_session.add(pp)
    await db_session.flush()

    pp.is_accepting_bookings = True
    await db_session.flush()

    fetched = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.id == pp.id)
    )).scalar_one()
    assert fetched.is_active is True
    assert fetched.is_accepting_bookings is True


@pytest.mark.asyncio
async def test_constructor_kwarg_is_accepting_bookings_routes_to_is_active(
    db_session: AsyncSession,
) -> None:
    """Tests + seed code construct ProviderProfile passing
    is_accepting_bookings=True. SQLAlchemy's declarative __init__ does
    setattr per kwarg, which routes through the @property.setter."""
    user = await _make_user(db_session, "e1e-ctor@test.com")
    pp = ProviderProfile(
        user_id=user.id,
        provider_type=ProviderType.DETAILER.value,
        is_accepting_bookings=False,
    )
    db_session.add(pp)
    await db_session.flush()

    fetched = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.id == pp.id)
    )).scalar_one()
    assert fetched.is_active is False
    assert fetched.is_accepting_bookings is False
