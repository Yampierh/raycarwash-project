"""
tests/test_workers_y6.py — Phase 5 chunk Y6 worker tests.

Drives `achievement_evaluator` and `document_expiry_checker` through
their `_*_with_session(session)` helpers — same pattern Phase 3's
worker tests use, so we don't spin up AsyncSessionLocal on a
different event loop than the fixture session.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.audit.models import AuditAction, AuditLog
from domains.auth.models import Role, UserRoleAssociation
from domains.providers.achievement import ProviderAchievement
from domains.providers.models import ProviderProfile
from domains.users.document import Document
from domains.users.models import User


# ─── factories ────────────────────────────────────────────────────────────────


async def _make_provider(
    db_session: AsyncSession,
    email: str,
    *,
    verification_status: str = "not_submitted",
    total_services_completed: int = 0,
    average_rating: float | None = None,
    total_reviews: int = 0,
) -> User:
    role = (await db_session.execute(
        select(Role).where(Role.name == "detailer")
    )).scalar_one()
    user = User(
        email=email,
        full_name="Worker Test",
        password_hash="$2b$12$abc",
        is_verified=True,
        onboarding_status="completed",
    )
    db_session.add(user)
    await db_session.flush()

    db_session.add(UserRoleAssociation(user_id=user.id, role_id=role.id))
    profile = ProviderProfile(
        user_id=user.id,
        business_name=email.split("@")[0],
        verification_status=verification_status,
        verification_reviewed_at=(
            datetime.now(timezone.utc) if verification_status == "approved" else None
        ),
        total_services_completed=total_services_completed,
        average_rating=average_rating,
        total_reviews=total_reviews,
    )
    db_session.add(profile)
    await db_session.flush()
    return user


# ─── achievement_evaluator ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_achievement_evaluator_grants_verified_badge(
    db_session: AsyncSession,
) -> None:
    from workers.achievement_evaluator import _evaluate_with_session

    user = await _make_provider(
        db_session, "ach-verif@test.com", verification_status="approved",
    )

    granted = await _evaluate_with_session(db_session)
    assert granted >= 1

    rows = (await db_session.scalars(
        select(ProviderAchievement)
        .where(ProviderAchievement.provider_user_id == user.id)
    )).all()
    types = {r.achievement_type for r in rows}
    assert "verified" in types


@pytest.mark.asyncio
async def test_achievement_evaluator_grants_milestone_badges(
    db_session: AsyncSession,
) -> None:
    from workers.achievement_evaluator import _evaluate_with_session

    user = await _make_provider(
        db_session, "ach-milestone@test.com",
        total_services_completed=120,  # crosses 1, 10, 100
    )
    await _evaluate_with_session(db_session)

    rows = (await db_session.scalars(
        select(ProviderAchievement)
        .where(ProviderAchievement.provider_user_id == user.id)
    )).all()
    types = {r.achievement_type for r in rows}
    assert {"first_job", "ten_jobs", "hundred_jobs"}.issubset(types)


@pytest.mark.asyncio
async def test_achievement_evaluator_grants_five_star_when_rating_qualifies(
    db_session: AsyncSession,
) -> None:
    from workers.achievement_evaluator import _evaluate_with_session

    user = await _make_provider(
        db_session, "ach-fivestar@test.com",
        average_rating=4.95, total_reviews=12,
    )
    await _evaluate_with_session(db_session)

    rows = (await db_session.scalars(
        select(ProviderAchievement)
        .where(ProviderAchievement.provider_user_id == user.id)
    )).all()
    assert any(r.achievement_type == "five_star" for r in rows)


@pytest.mark.asyncio
async def test_achievement_evaluator_does_not_grant_five_star_below_review_threshold(
    db_session: AsyncSession,
) -> None:
    from workers.achievement_evaluator import _evaluate_with_session

    user = await _make_provider(
        db_session, "ach-fivestar-low@test.com",
        average_rating=4.9, total_reviews=2,  # < 5 reviews
    )
    await _evaluate_with_session(db_session)

    rows = (await db_session.scalars(
        select(ProviderAchievement)
        .where(
            ProviderAchievement.provider_user_id == user.id,
            ProviderAchievement.achievement_type == "five_star",
        )
    )).all()
    assert rows == []


@pytest.mark.asyncio
async def test_achievement_evaluator_is_idempotent_across_runs(
    db_session: AsyncSession,
) -> None:
    """Re-running the worker for an already-decorated provider must be
    a no-op — the (provider_user_id, achievement_type) UNIQUE makes
    this an ON CONFLICT DO NOTHING insert."""
    from workers.achievement_evaluator import _evaluate_with_session

    user = await _make_provider(
        db_session, "ach-idem@test.com", verification_status="approved",
    )
    first = await _evaluate_with_session(db_session)
    second = await _evaluate_with_session(db_session)
    third = await _evaluate_with_session(db_session)

    assert first >= 1
    assert second == 0
    assert third == 0

    rows = (await db_session.scalars(
        select(ProviderAchievement)
        .where(
            ProviderAchievement.provider_user_id == user.id,
            ProviderAchievement.achievement_type == "verified",
        )
    )).all()
    assert len(rows) == 1


# ─── document_expiry_checker ──────────────────────────────────────────────────


async def _make_document(
    db_session: AsyncSession,
    user: User,
    *,
    expires_at: date | None,
    doc_type: str = "insurance",
) -> Document:
    doc = Document(
        user_id=user.id,
        type=doc_type,
        title="Test policy",
        s3_key=f"documents/{user.id}/{doc_type}/{uuid.uuid4().hex}.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        expires_at=expires_at,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest.mark.asyncio
async def test_expiry_checker_skips_docs_outside_threshold(
    db_session: AsyncSession,
) -> None:
    from workers.document_expiry_checker import _check_with_session

    user = await _make_provider(db_session, "exp-skip@test.com")
    await _make_document(
        db_session, user, expires_at=date.today() + timedelta(days=90),
    )

    dispatched = await _check_with_session(db_session)
    assert dispatched == 0


@pytest.mark.asyncio
async def test_expiry_checker_dispatches_within_30d_window(
    db_session: AsyncSession,
) -> None:
    from workers.document_expiry_checker import _check_with_session

    user = await _make_provider(db_session, "exp-hit@test.com")
    doc = await _make_document(
        db_session, user, expires_at=date.today() + timedelta(days=20),
    )

    dispatched = await _check_with_session(db_session)
    assert dispatched == 1

    # Audit row stamps the (doc, bucket) so we don't re-send.
    audits = (await db_session.scalars(
        select(AuditLog)
        .where(
            AuditLog.entity_type == "document",
            AuditLog.entity_id == str(doc.id),
        )
    )).all()
    bucket_rows = [
        a for a in audits
        if a.metadata_ and a.metadata_.get("source") == "document_expiry_checker"
    ]
    assert len(bucket_rows) == 1
    assert bucket_rows[0].metadata_["reminder_bucket"] in (30, 14, 7, 1)


@pytest.mark.asyncio
async def test_expiry_checker_is_idempotent_per_bucket(
    db_session: AsyncSession,
) -> None:
    """Running twice in the same bucket must not re-dispatch."""
    from workers.document_expiry_checker import _check_with_session

    user = await _make_provider(db_session, "exp-idem@test.com")
    await _make_document(
        db_session, user, expires_at=date.today() + timedelta(days=5),
    )

    first = await _check_with_session(db_session)
    second = await _check_with_session(db_session)

    assert first == 1
    assert second == 0


@pytest.mark.asyncio
async def test_expiry_checker_skips_deleted_documents(
    db_session: AsyncSession,
) -> None:
    from workers.document_expiry_checker import _check_with_session

    user = await _make_provider(db_session, "exp-deleted@test.com")
    doc = await _make_document(
        db_session, user, expires_at=date.today() + timedelta(days=3),
    )
    doc.is_deleted = True
    doc.deleted_at = datetime.now(timezone.utc)
    await db_session.flush()

    dispatched = await _check_with_session(db_session)
    assert dispatched == 0


# ─── schedule registration ────────────────────────────────────────────────────


def test_schedule_includes_y6_jobs() -> None:
    from workers import schedule

    ids = {d["id"] for d in schedule._JOB_DEFS}
    assert "achievement_evaluator" in ids
    assert "document_expiry_checker" in ids
