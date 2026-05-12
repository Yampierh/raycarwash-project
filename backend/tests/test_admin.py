"""
test_admin.py

Admin API tests — covers all /api/v1/admin/* endpoints.

Tests:
  - Auth guard: non-admin users get 403
  - Stats endpoint returns expected shape
  - User list: pagination, search, role filter, ban/unban
  - User detail + role assignment/revocation
  - Role CRUD (create, update, delete — system roles protected)
  - Permission CRUD
  - Role ↔ Permission assignment
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import _create_user_with_role, get_access_token


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _admin_token(client: AsyncClient, db_session: AsyncSession) -> str:
    admin = await _create_user_with_role(
        db_session, "admin@test.com", "Admin User", "admin"
    )
    return await get_access_token(client, "admin@test.com")


async def _admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    token = await _admin_token(client, db_session)
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Auth guards
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminAuthGuards:

    @pytest.mark.asyncio
    async def test_stats_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/stats")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_stats_requires_admin_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "regular@test.com", "Regular", "client")
        token = await get_access_token(client, "regular@test.com")
        resp = await client.get(
            "/api/v1/admin/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_detailer_cannot_access_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        await _create_user_with_role(db_session, "det@test.com", "Det", "detailer")
        token = await get_access_token(client, "det@test.com")
        resp = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminStats:

    @pytest.mark.asyncio
    async def test_stats_returns_expected_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get("/api/v1/admin/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        for key in (
            "total_users", "active_users", "total_detailers",
            "total_clients", "pending_verification",
            "total_appointments", "total_roles", "total_permissions",
        ):
            assert key in data, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_stats_counts_reflect_created_users(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _create_user_with_role(db_session, "c1@test.com", "C1", "client")
        await _create_user_with_role(db_session, "d1@test.com", "D1", "detailer")

        resp = await client.get("/api/v1/admin/stats", headers=headers)
        data = resp.json()
        # admin + client + detailer = 3 total (at least)
        assert data["total_users"] >= 3
        assert data["total_clients"] >= 1
        assert data["total_detailers"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# Users list
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminUsersList:

    @pytest.mark.asyncio
    async def test_users_list_returns_paginated_response(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get("/api/v1/admin/users", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    @pytest.mark.asyncio
    async def test_users_list_default_page(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get("/api/v1/admin/users", headers=headers)
        data = resp.json()
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_users_list_search_by_email(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _create_user_with_role(db_session, "findme@test.com", "Find Me", "client")

        resp = await client.get(
            "/api/v1/admin/users?search=findme", headers=headers
        )
        data = resp.json()
        assert any("findme" in u["email"] for u in data["users"])

    @pytest.mark.asyncio
    async def test_users_list_filter_by_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        await _create_user_with_role(db_session, "rolefilter@test.com", "Role Filter", "client")

        resp = await client.get(
            "/api/v1/admin/users?role=client", headers=headers
        )
        data = resp.json()
        for user in data["users"]:
            assert "client" in user["roles"]

    @pytest.mark.asyncio
    async def test_users_list_per_page(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get(
            "/api/v1/admin/users?per_page=1", headers=headers
        )
        data = resp.json()
        assert len(data["users"]) <= 1


# ─────────────────────────────────────────────────────────────────────────────
# User detail
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminUserDetail:

    @pytest.mark.asyncio
    async def test_get_user_detail(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        target = await _create_user_with_role(db_session, "detail@test.com", "Detail User", "client")

        resp = await client.get(f"/api/v1/admin/users/{target.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "detail@test.com"
        assert "client" in data["roles"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        import uuid
        headers = await _admin_headers(client, db_session)
        resp = await client.get(
            f"/api/v1/admin/users/{uuid.uuid4()}", headers=headers
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_ban_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        target = await _create_user_with_role(db_session, "ban@test.com", "Ban User", "client")

        resp = await client.patch(
            f"/api/v1/admin/users/{target.id}",
            json={"is_active": False},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_unban_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        target = await _create_user_with_role(db_session, "unban@test.com", "Unban User", "client")

        await client.patch(
            f"/api/v1/admin/users/{target.id}", json={"is_active": False}, headers=headers
        )
        resp = await client.patch(
            f"/api/v1/admin/users/{target.id}", json={"is_active": True}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Role CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminRoles:

    @pytest.mark.asyncio
    async def test_list_roles_returns_system_roles(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get("/api/v1/admin/roles", headers=headers)
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()]
        assert "admin" in names
        assert "client" in names
        assert "detailer" in names

    @pytest.mark.asyncio
    async def test_create_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            "/api/v1/admin/roles",
            json={"name": "moderator", "description": "Content moderator"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "moderator"
        assert data["is_system"] is False

    @pytest.mark.asyncio
    async def test_update_custom_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        created = await client.post(
            "/api/v1/admin/roles",
            json={"name": "temp_role", "description": "Temporary"},
            headers=headers,
        )
        role_id = created.json()["id"]

        resp = await client.patch(
            f"/api/v1/admin/roles/{role_id}",
            json={"description": "Updated description"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_custom_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        created = await client.post(
            "/api/v1/admin/roles",
            json={"name": "delete_me_role"},
            headers=headers,
        )
        role_id = created.json()["id"]

        resp = await client.delete(f"/api/v1/admin/roles/{role_id}", headers=headers)
        assert resp.status_code == 204

        # Verify gone from list
        roles = await client.get("/api/v1/admin/roles", headers=headers)
        assert not any(r["id"] == role_id for r in roles.json())

    @pytest.mark.asyncio
    async def test_cannot_delete_system_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        roles = await client.get("/api/v1/admin/roles", headers=headers)
        admin_role = next(r for r in roles.json() if r["name"] == "admin")

        resp = await client.delete(
            f"/api/v1/admin/roles/{admin_role['id']}", headers=headers
        )
        # System roles are protected — 409 Conflict
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_cannot_update_system_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        roles = await client.get("/api/v1/admin/roles", headers=headers)
        client_role = next(r for r in roles.json() if r["name"] == "client")

        resp = await client.patch(
            f"/api/v1/admin/roles/{client_role['id']}",
            json={"name": "hacked"},
            headers=headers,
        )
        # System roles return 404 (update_role returns None for system roles)
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Permission CRUD
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminPermissions:

    @pytest.mark.asyncio
    async def test_list_permissions_returns_seeded_permissions(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.get("/api/v1/admin/permissions", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 18  # 18 seeded permissions
        names = [p["name"] for p in data]
        assert "read:users" in names
        assert "write:appointments" in names

    @pytest.mark.asyncio
    async def test_create_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            "/api/v1/admin/permissions",
            json={
                "name": "read:analytics",
                "resource": "analytics",
                "action": "read",
                "description": "View analytics dashboard",
            },
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "read:analytics"
        assert data["resource"] == "analytics"

    @pytest.mark.asyncio
    async def test_delete_permission(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        created = await client.post(
            "/api/v1/admin/permissions",
            json={"name": "delete:temp", "resource": "temp", "action": "delete"},
            headers=headers,
        )
        perm_id = created.json()["id"]

        resp = await client.delete(f"/api/v1/admin/permissions/{perm_id}", headers=headers)
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_permission_name_must_follow_format(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        resp = await client.post(
            "/api/v1/admin/permissions",
            json={"name": "INVALID_FORMAT", "resource": "x", "action": "y"},
            headers=headers,
        )
        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Role ↔ Permission assignment
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminRolePermissions:

    @pytest.mark.asyncio
    async def test_assign_permission_to_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)

        # Create a custom role
        role_resp = await client.post(
            "/api/v1/admin/roles",
            json={"name": "custom_assignee"},
            headers=headers,
        )
        role_id = role_resp.json()["id"]

        # Create a custom permission
        perm_resp = await client.post(
            "/api/v1/admin/permissions",
            json={"name": "read:custom", "resource": "custom", "action": "read"},
            headers=headers,
        )
        perm_id = perm_resp.json()["id"]

        # Assign
        resp = await client.post(
            f"/api/v1/admin/roles/{role_id}/permissions",
            json={"permission_id": perm_id},
            headers=headers,
        )
        assert resp.status_code == 201

        # Verify it appears in role detail
        roles = await client.get("/api/v1/admin/roles", headers=headers)
        target = next(r for r in roles.json() if r["id"] == role_id)
        assert any(p["id"] == perm_id for p in target["permissions"])

    @pytest.mark.asyncio
    async def test_revoke_permission_from_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)

        role_resp = await client.post(
            "/api/v1/admin/roles", json={"name": "revoke_test_role"}, headers=headers
        )
        role_id = role_resp.json()["id"]

        perm_resp = await client.post(
            "/api/v1/admin/permissions",
            json={"name": "write:tempresource", "resource": "tempresource", "action": "write"},
            headers=headers,
        )
        perm_id = perm_resp.json()["id"]

        await client.post(
            f"/api/v1/admin/roles/{role_id}/permissions",
            json={"permission_id": perm_id},
            headers=headers,
        )

        resp = await client.delete(
            f"/api/v1/admin/roles/{role_id}/permissions/{perm_id}",
            headers=headers,
        )
        assert resp.status_code == 204

        roles = await client.get("/api/v1/admin/roles", headers=headers)
        target = next(r for r in roles.json() if r["id"] == role_id)
        assert not any(p["id"] == perm_id for p in target["permissions"])


# ─────────────────────────────────────────────────────────────────────────────
# User role assignment
# ─────────────────────────────────────────────────────────────────────────────

class TestAdminUserRoles:

    @pytest.mark.asyncio
    async def test_assign_role_to_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        target = await _create_user_with_role(db_session, "roleuser@test.com", "Role User", "client")

        # Get detailer role id
        roles = await client.get("/api/v1/admin/roles", headers=headers)
        detailer_role = next(r for r in roles.json() if r["name"] == "detailer")

        resp = await client.post(
            f"/api/v1/admin/users/{target.id}/roles",
            json={"role_id": detailer_role["id"]},
            headers=headers,
        )
        assert resp.status_code == 201

        detail = await client.get(f"/api/v1/admin/users/{target.id}", headers=headers)
        assert "detailer" in detail.json()["roles"]

    @pytest.mark.asyncio
    async def test_revoke_role_from_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        headers = await _admin_headers(client, db_session)
        target = await _create_user_with_role(db_session, "revokerole@test.com", "Revoke", "client")

        roles = await client.get("/api/v1/admin/roles", headers=headers)
        client_role = next(r for r in roles.json() if r["name"] == "client")

        resp = await client.delete(
            f"/api/v1/admin/users/{target.id}/roles/{client_role['id']}",
            headers=headers,
        )
        assert resp.status_code == 204

        detail = await client.get(f"/api/v1/admin/users/{target.id}", headers=headers)
        assert "client" not in detail.json()["roles"]
