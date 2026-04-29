from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/users", tags=["Users"])

# Registration is handled by POST /auth/register.
# This router is reserved for future user-management endpoints
# (e.g. GET /api/v1/users/me, PATCH /api/v1/users/{id}, admin listing).
