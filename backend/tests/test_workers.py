"""
tests/test_workers.py — Phase 3 chunk P workers.

Each worker is invoked directly as a function (the RQ scheduler is just
the cron, the actual work is the function body) so the tests don't need
Redis. We seed expired rows by writing through the same AsyncSession the
worker opens internally.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import UserLoginHistory
from domains.users.pending_contact_change import PendingContactChange


async def _make_user(db_session: AsyncSession) -> uuid.UUID:
    """Insert a minimal user so the FK from the worker's target tables
    holds. Returns the new user_id."""
    from sqlalchemy import text
    user_id = uuid.uuid4()
    await db_session.execute(
        text(
            "INSERT INTO users "
            "(id, email, full_name, password_hash, is_active, is_verified, "
            " failed_login_attempts, onboarding_status, token_version, "
            " preferred_language, preferred_timezone, "
            " created_at, updated_at, is_deleted) "
            "VALUES (:id, :email, NULL, 'x', true, false, 0, 'pending_profile', 1, "
            "        'en', 'America/Indiana/Indianapolis', NOW(), NOW(), false)"
        ),
        {"id": user_id, "email": f"{user_id}@test.com"},
    )
    await db_session.commit()
    return user_id


# ─── pending_contact_cleanup ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_contact_cleanup_removes_expired_unconsumed(
    db_session: AsyncSession,
) -> None:
    user_id = await _make_user(db_session)

    now = datetime.now(timezone.utc)
    # Expired + unconsumed → should be deleted.
    expired = PendingContactChange(
        user_id=user_id,
        change_type="email",
        new_value_encrypted="old@test.com",
        new_value_hash="hash-old",
        verification_token_hash="th-old",
        attempts=0,
        created_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
    )
    # Expired but consumed → KEEP (audit trail).
    consumed = PendingContactChange(
        user_id=user_id,
        change_type="email",
        new_value_encrypted="consumed@test.com",
        new_value_hash="hash-consumed",
        verification_token_hash="th-consumed",
        attempts=0,
        created_at=now - timedelta(hours=3),
        expires_at=now - timedelta(hours=2),
        consumed_at=now - timedelta(hours=2),
    )
    # Active (not expired) → KEEP.
    active = PendingContactChange(
        user_id=user_id,
        change_type="phone",
        new_value_encrypted="+15558887777",
        new_value_hash="hash-active",
        verification_token_hash="th-active",
        attempts=0,
        created_at=now,
        expires_at=now + timedelta(minutes=8),
    )
    db_session.add_all([expired, consumed, active])
    await db_session.commit()

    from workers.pending_contact_cleanup import _cleanup_with_session
    removed = await _cleanup_with_session(db_session)
    await db_session.commit()
    assert removed == 1

    remaining = (
        await db_session.execute(
            select(PendingContactChange).where(PendingContactChange.user_id == user_id)
        )
    ).scalars().all()
    assert {r.new_value_hash for r in remaining} == {"hash-consumed", "hash-active"}


# ─── login_history_purger ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_history_purger_drops_old_rows(db_session: AsyncSession) -> None:
    user_id = await _make_user(db_session)
    now = datetime.now(timezone.utc)

    rows = [
        # Successful from 14 months ago → purge (over 12-month retention).
        UserLoginHistory(
            user_id=user_id,
            login_at=now - timedelta(days=14 * 30),
            ip_address="1.2.3.4",
            user_agent="old-success",
            auth_method="password",
            was_successful=True,
        ),
        # Successful from 6 months ago → keep.
        UserLoginHistory(
            user_id=user_id,
            login_at=now - timedelta(days=180),
            ip_address="1.2.3.4",
            user_agent="recent-success",
            auth_method="password",
            was_successful=True,
        ),
        # Failed from 4 months ago → purge (over 90-day retention).
        UserLoginHistory(
            user_id=user_id,
            login_at=now - timedelta(days=120),
            ip_address="9.9.9.9",
            user_agent="old-fail",
            auth_method="password",
            was_successful=False,
            failure_reason="invalid_password",
        ),
        # Failed from 60 days ago → keep.
        UserLoginHistory(
            user_id=user_id,
            login_at=now - timedelta(days=60),
            ip_address="9.9.9.9",
            user_agent="recent-fail",
            auth_method="password",
            was_successful=False,
            failure_reason="invalid_password",
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()

    from workers.login_history_purger import _purge_with_session
    stats = await _purge_with_session(db_session)
    await db_session.commit()

    assert stats["successful_purged"] == 1
    assert stats["failed_purged"] == 1

    remaining = (
        await db_session.execute(
            select(UserLoginHistory).where(UserLoginHistory.user_id == user_id)
        )
    ).scalars().all()
    user_agents = {r.user_agent for r in remaining}
    assert user_agents == {"recent-success", "recent-fail"}


# ─── schedule.py imports cleanly ──────────────────────────────────────────────


def test_schedule_module_imports_and_defines_jobs() -> None:
    """`workers.schedule` should be importable without contacting Redis;
    register_all() is the only function that opens a connection."""
    from workers import schedule
    assert len(schedule._JOB_DEFS) >= 2
    ids = {d["id"] for d in schedule._JOB_DEFS}
    assert "pending_contact_cleanup" in ids
    assert "login_history_purger" in ids
