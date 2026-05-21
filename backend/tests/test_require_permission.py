"""
tests/test_require_permission.py — Plan 23 Fase 3.

Covers the `require_permission(action, resource)` machinery:

  - _has_permission_cached() — cold cache populates Redis, hot cache
    skips the DB, wildcard `*:*` matches everything, redis failures
    fall back to direct DB lookup.
  - invalidate_permission_cache() — drops the key; no-op when redis is None.
  - The role-assignment endpoint (`POST /api/v1/admin/users/{id}/roles`)
    calls invalidate_permission_cache(target_user_id, redis) so newly
    granted permissions take effect within seconds, not minutes.

The end-to-end "non-admin user with permission X passes / without fails"
flow is best exercised once we migrate a real endpoint to
require_permission — kept out of scope here per plan §F3 D2 note.
"""
from __future__ import annotations

import json as _json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.models import Role
from domains.auth.service import (
    _has_permission_cached,
    invalidate_permission_cache,
)
from tests.conftest import _create_user_with_role, get_access_token


# ── _has_permission_cached unit ────────────────────────────────────── #


class TestHasPermissionCached:
    @pytest.mark.asyncio
    async def test_cache_populated_on_miss(self, db_session: AsyncSession):
        user = await _create_user_with_role(db_session, "cache-1@test.com", "C1", "client")
        # client role doesn't carry write:users
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        result = await _has_permission_cached(user, "write:users", redis, db=db_session)
        assert result is False
        # cache was populated for next call
        redis.setex.assert_called_once()
        key, ttl, value = redis.setex.call_args.args
        assert key == f"permissions:{user.id}"
        assert ttl == 600
        assert isinstance(_json.loads(value), list)

    @pytest.mark.asyncio
    async def test_cache_hit_skips_db(self, db_session: AsyncSession):
        """When the cache claims write:users, we trust it even if the DB
        wouldn't grant it — this is the contract: cache is authoritative
        within its TTL and gets invalidated on mutation."""
        user = await _create_user_with_role(db_session, "cache-2@test.com", "C2", "client")
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=_json.dumps(["write:users"]))
        redis.setex = AsyncMock()

        result = await _has_permission_cached(user, "write:users", redis, db=db_session)
        assert result is True
        redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_wildcard_grant_matches_anything(self, db_session: AsyncSession):
        user = await _create_user_with_role(db_session, "wild@test.com", "W", "client")
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=_json.dumps(["*:*"]))

        assert await _has_permission_cached(user, "anything:any_resource", redis, db=db_session) is True
        assert await _has_permission_cached(user, "delete:users", redis, db=db_session) is True

    @pytest.mark.asyncio
    async def test_redis_failure_falls_back_to_db(self, db_session: AsyncSession):
        user = await _create_user_with_role(db_session, "rf@test.com", "RF", "client")
        redis = AsyncMock()
        redis.get = AsyncMock(side_effect=Exception("redis down"))
        redis.setex = AsyncMock(side_effect=Exception("redis down"))

        # Falls through to user.get_all_permissions(); client role does
        # NOT have write:users.
        result = await _has_permission_cached(user, "write:users", redis, db=db_session)
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_none_uses_db_directly(self, db_session: AsyncSession):
        user = await _create_user_with_role(db_session, "norr@test.com", "N", "client")
        # client role does have read:appointments per seed_rbac
        assert await _has_permission_cached(user, "read:appointments", None, db=db_session) is True
        assert await _has_permission_cached(user, "write:users", None, db=db_session) is False


# ── invalidate_permission_cache ────────────────────────────────────── #


class TestInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_drops_key(self):
        redis = AsyncMock()
        redis.delete = AsyncMock()
        uid = uuid.uuid4()
        await invalidate_permission_cache(uid, redis)
        redis.delete.assert_called_once_with(f"permissions:{uid}")

    @pytest.mark.asyncio
    async def test_invalidate_redis_none_is_noop(self):
        await invalidate_permission_cache(uuid.uuid4(), None)

    @pytest.mark.asyncio
    async def test_invalidate_swallows_redis_errors(self):
        redis = AsyncMock()
        redis.delete = AsyncMock(side_effect=Exception("redis down"))
        # Must not raise — caller path (admin endpoints) shouldn't 500
        # because the cache is sick.
        await invalidate_permission_cache(uuid.uuid4(), redis)


# ── Role-mutation endpoints invalidate the cache ───────────────────── #


class TestRoleMutationInvalidatesCache:
    @pytest.mark.asyncio
    async def test_assign_role_invalidates_target_user_cache(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        await _create_user_with_role(db_session, "rm-admin@test.com", "A", "admin")
        target = await _create_user_with_role(db_session, "rm-target@test.com", "T", "client")
        admin_token = await get_access_token(client, "rm-admin@test.com")

        new_role = (await db_session.execute(
            select(Role).where(Role.name == "detailer")
        )).scalar_one()

        with patch("domains.admin.router.invalidate_permission_cache", new=AsyncMock()) as mock:
            resp = await client.post(
                f"/api/v1/admin/users/{target.id}/roles",
                json={"role_id": str(new_role.id)},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp.status_code == 201
            mock.assert_awaited_once()
            # Called with (target_user_id, redis)
            assert mock.await_args.args[0] == target.id

    @pytest.mark.asyncio
    async def test_revoke_role_invalidates_target_user_cache(
        self, client: AsyncClient, db_session: AsyncSession,
    ):
        from domains.auth.models import UserRoleAssociation

        await _create_user_with_role(db_session, "rev-admin@test.com", "A", "admin")
        target = await _create_user_with_role(db_session, "rev-target@test.com", "T", "client")
        admin_token = await get_access_token(client, "rev-admin@test.com")

        client_role = (await db_session.execute(
            select(Role).where(Role.name == "client")
        )).scalar_one()

        with patch("domains.admin.router.invalidate_permission_cache", new=AsyncMock()) as mock:
            resp = await client.delete(
                f"/api/v1/admin/users/{target.id}/roles/{client_role.id}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp.status_code == 204
            mock.assert_awaited_once()
            assert mock.await_args.args[0] == target.id
