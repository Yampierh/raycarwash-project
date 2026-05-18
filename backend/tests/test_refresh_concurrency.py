"""
tests/test_refresh_concurrency.py — Hotfix H1.

Regression guard for the refresh-token TOCTOU race fixed in
AuthService.rotate_refresh_token + RefreshTokenRepository.mark_used_atomic.

Failure mode before the fix: two concurrent rotations of the same
single-use refresh token could both pass the `used_at IS NULL` check,
both call `mark_used`, and both emit fresh access+refresh pairs — so
the "single-use" guarantee was violated.

The fix swaps `mark_used` for an atomic
    UPDATE … SET used_at=now()
    WHERE id=? AND used_at IS NULL AND revoked IS FALSE
where exactly one caller observes rowcount=1; the loser revokes the
family and returns 401.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import RefreshToken
from domains.auth.refresh_token_repository import RefreshTokenRepository
from domains.auth.service import AuthService


@pytest.mark.asyncio
async def test_mark_used_atomic_returns_true_on_first_claim(db_session: AsyncSession, test_user):
    """Single caller successfully claims a fresh token (rowcount=1)."""
    raw = await AuthService.create_refresh_token(
        subject=test_user.id,
        role_name="client",
        db=db_session,
    )
    repo = RefreshTokenRepository(db_session)
    row = await repo.get_by_raw(raw)
    assert row is not None
    assert row.used_at is None

    claimed = await repo.mark_used_atomic(row.id)
    assert claimed is True

    refreshed = await db_session.get(RefreshToken, row.id)
    assert refreshed.used_at is not None


@pytest.mark.asyncio
async def test_mark_used_atomic_returns_false_on_already_used(db_session: AsyncSession, test_user):
    """Second caller on an already-used token observes rowcount=0."""
    raw = await AuthService.create_refresh_token(
        subject=test_user.id,
        role_name="client",
        db=db_session,
    )
    repo = RefreshTokenRepository(db_session)
    row = await repo.get_by_raw(raw)
    assert row is not None

    first = await repo.mark_used_atomic(row.id)
    second = await repo.mark_used_atomic(row.id)
    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_mark_used_atomic_returns_false_on_revoked(db_session: AsyncSession, test_user):
    """Revoked tokens cannot be claimed even if used_at is still NULL."""
    raw = await AuthService.create_refresh_token(
        subject=test_user.id,
        role_name="client",
        db=db_session,
    )
    repo = RefreshTokenRepository(db_session)
    row = await repo.get_by_raw(raw)
    assert row is not None

    await repo.revoke_family(row.family_id)
    await db_session.flush()
    claimed = await repo.mark_used_atomic(row.id)
    assert claimed is False


@pytest.mark.asyncio
async def test_rotate_refresh_token_lost_race_revokes_family(
    db_session: AsyncSession, test_user
):
    """Simulate the race by manually claiming the row before rotate runs.

    rotate_refresh_token MUST treat rowcount=0 as theft/race: revoke the
    family and raise 401. We can't reliably gather() two real rotations
    against the same session (asyncpg single-connection serialization
    would defeat the race), so we simulate the lost-race path by
    pre-claiming the token directly.
    """
    raw = await AuthService.create_refresh_token(
        subject=test_user.id,
        role_name="client",
        db=db_session,
    )
    repo = RefreshTokenRepository(db_session)
    row = await repo.get_by_raw(raw)
    assert row is not None

    # Race winner: claim the token out-of-band.
    assert await repo.mark_used_atomic(row.id) is True
    await db_session.flush()

    # Race loser: rotate now sees used_at IS NOT NULL via the reuse branch,
    # OR a freshly-fetched row that still appears unused will lose the
    # atomic claim. Either path must end in family revocation + 401.
    with pytest.raises(HTTPException) as exc:
        await AuthService.rotate_refresh_token(raw, db_session)
    assert exc.value.status_code == 401

    # Family revoked — all tokens in the family flipped to revoked=True.
    stmt = select(RefreshToken).where(RefreshToken.family_id == row.family_id)
    result = await db_session.execute(stmt)
    for token in result.scalars().all():
        assert token.revoked is True, (
            "every token in the family must be revoked after a lost race"
        )


@pytest.mark.asyncio
async def test_rotate_refresh_token_happy_path_still_works(
    db_session: AsyncSession, test_user
):
    """Sanity: a single, uncontested rotation succeeds and the new token is
    independently rotatable."""
    raw = await AuthService.create_refresh_token(
        subject=test_user.id,
        role_name="client",
        db=db_session,
    )
    new_access, new_refresh = await AuthService.rotate_refresh_token(raw, db_session)
    assert new_access and new_refresh
    assert new_refresh != raw

    # The new refresh can itself be rotated, proving the family is intact.
    next_access, next_refresh = await AuthService.rotate_refresh_token(
        new_refresh, db_session
    )
    assert next_access and next_refresh
