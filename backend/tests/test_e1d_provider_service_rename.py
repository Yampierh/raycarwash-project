"""
tests/test_e1d_provider_service_rename.py — Integration plan E1 chunk D.

Schema-level invariants for the rename:
  * `DetailerService` is preserved as an alias of `ProviderService` so
    legacy imports keep working.
  * The underlying table is `provider_services` and the FK column is
    `provider_id` (not `detailer_id`).
  * `ProviderProfile.provider_services` is the canonical relationship;
    `.detailer_services` is a back-compat property returning the same
    list.
  * `provider_service_categories` is a working m2m junction — a provider
    can be associated with multiple categories via
    `ProviderProfile.service_categories_rel`.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.providers.models import ProviderProfile, ProviderType
from domains.services_catalog.models import (
    DetailerService,
    ProviderService,
    ProviderServiceCategory,
    Service,
    ServiceCategory,
    ServiceCategoryTable,
)
from domains.users.models import User


async def _make_user(db: AsyncSession, email: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name="E1D Tester",
        password_hash="x",
    )
    db.add(user)
    await db.flush()
    return user


async def _make_provider(
    db: AsyncSession, user: User, provider_type: ProviderType = ProviderType.DETAILER,
) -> ProviderProfile:
    pp = ProviderProfile(user_id=user.id, provider_type=provider_type.value)
    db.add(pp)
    await db.flush()
    return pp


async def _first_service(db: AsyncSession) -> Service:
    svc = (await db.execute(
        select(Service).where(Service.is_active.is_(True)).limit(1)
    )).scalar_one()
    return svc


async def _seed_category(db: AsyncSession, slug: str, name: str) -> ServiceCategoryTable:
    existing = (await db.execute(
        select(ServiceCategoryTable).where(ServiceCategoryTable.slug == slug)
    )).scalar_one_or_none()
    if existing:
        return existing
    row = ServiceCategoryTable(slug=slug, name=name)
    db.add(row)
    await db.flush()
    return row


# ─── Class alias ─────────────────────────────────────────────────────────────


def test_detailer_service_is_alias_of_provider_service() -> None:
    """Legacy `from ...models import DetailerService` keeps resolving to
    ProviderService. Removing this alias is a code-only follow-up."""
    assert DetailerService is ProviderService


# ─── Table / column rename ───────────────────────────────────────────────────


def test_provider_service_table_and_column_are_renamed() -> None:
    assert ProviderService.__tablename__ == "provider_services"
    cols = {c.name for c in ProviderService.__table__.columns}
    assert "provider_id" in cols
    assert "detailer_id" not in cols


# ─── Relationship rename + back-compat property ──────────────────────────────


@pytest.mark.asyncio
async def test_provider_services_relationship_uses_new_name(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1d-rel@test.com")
    pp = await _make_provider(db_session, user)
    svc = await _first_service(db_session)
    db_session.add(ProviderService(
        provider_id=pp.id, service_id=svc.id,
        custom_price_cents=4500, is_active=True,
    ))
    await db_session.flush()

    fetched = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.id == pp.id)
    )).scalar_one()
    assert len(fetched.provider_services) == 1
    assert fetched.provider_services[0].custom_price_cents == 4500


@pytest.mark.asyncio
async def test_legacy_detailer_services_property_still_works(
    db_session: AsyncSession,
) -> None:
    """Code that hasn't been migrated yet keeps reading `pp.detailer_services`
    and gets the same list as `pp.provider_services`."""
    user = await _make_user(db_session, "e1d-bc@test.com")
    pp = await _make_provider(db_session, user)
    svc = await _first_service(db_session)
    db_session.add(ProviderService(
        provider_id=pp.id, service_id=svc.id,
    ))
    await db_session.flush()

    fetched = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.id == pp.id)
    )).scalar_one()
    assert fetched.detailer_services == fetched.provider_services
    assert len(fetched.detailer_services) == 1


# ─── m2m service_categories ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_provider_can_link_multiple_service_categories(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, "e1d-m2m@test.com")
    pp = await _make_provider(db_session, user)
    cat_a = await _seed_category(db_session, "basic_wash_test", "Basic Wash (test)")
    cat_b = await _seed_category(db_session, "interior_detail_test", "Interior Detail (test)")
    db_session.add(ProviderServiceCategory(provider_id=pp.id, category_id=cat_a.id))
    db_session.add(ProviderServiceCategory(provider_id=pp.id, category_id=cat_b.id))
    await db_session.flush()

    fetched = (await db_session.execute(
        select(ProviderProfile).where(ProviderProfile.id == pp.id)
    )).scalar_one()
    slugs = {c.slug for c in fetched.service_categories_rel}
    assert slugs == {"basic_wash_test", "interior_detail_test"}


@pytest.mark.asyncio
async def test_service_category_m2m_pk_prevents_duplicates(
    db_session: AsyncSession,
) -> None:
    """(provider_id, category_id) is the PK — adding the same pair twice
    must violate the constraint."""
    from sqlalchemy.exc import IntegrityError

    user = await _make_user(db_session, "e1d-m2m-dup@test.com")
    pp = await _make_provider(db_session, user)
    cat = await _seed_category(db_session, "full_detail_test", "Full Detail (test)")
    db_session.add(ProviderServiceCategory(provider_id=pp.id, category_id=cat.id))
    await db_session.flush()
    db_session.add(ProviderServiceCategory(provider_id=pp.id, category_id=cat.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_deleting_provider_cascades_service_categories(
    db_session: AsyncSession,
) -> None:
    """Deleting a ProviderProfile must cascade-clean its junction rows so
    we don't leave dangling references."""
    user = await _make_user(db_session, "e1d-m2m-cascade@test.com")
    pp = await _make_provider(db_session, user)
    cat = await _seed_category(db_session, "ceramic_test", "Ceramic (test)")
    db_session.add(ProviderServiceCategory(provider_id=pp.id, category_id=cat.id))
    await db_session.flush()

    await db_session.delete(pp)
    await db_session.flush()

    remaining = (await db_session.execute(
        select(ProviderServiceCategory).where(
            ProviderServiceCategory.provider_id == pp.id
        )
    )).scalars().all()
    assert remaining == []


# ─── service_category_id column was dropped ──────────────────────────────────


def test_provider_profile_no_longer_has_service_category_id_column() -> None:
    cols = {c.name for c in ProviderProfile.__table__.columns}
    assert "service_category_id" not in cols
