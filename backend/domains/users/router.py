from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.audit.models import AuditAction
from domains.auth.models import Role, UserRoleAssociation
from domains.users.models import User
from domains.users.repository import UserRepository
from domains.users.schemas import UserCreate, UserRead
from domains.audit.repository import AuditRepository
from domains.auth.service import AuthService
from shared.schemas import ErrorDetail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new CLIENT or DETAILER account.",
    responses={
        409: {"model": ErrorDetail, "description": "Email already registered."},
    },
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """
    Open registration. ADMIN role is blocked at the schema layer.
    Password is bcrypt-hashed by AuthService — never stored in plaintext.
    """
    user_repo = UserRepository(db)

    if await user_repo.email_exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorDetail(
                code="EMAIL_TAKEN",
                message=f"An account with '{payload.email}' already exists.",
            ).model_dump(),
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        password_hash=AuthService.hash_password(payload.password),
    )

    created = await user_repo.create(user)

    role_names = payload.role_names or ["client"]
    for role_name in role_names:
        if role_name == "admin":
            continue
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if role:
            user_role = UserRoleAssociation(
                user_id=created.id,
                role_id=role.id,
            )
            db.add(user_role)

    await db.commit()
    await db.refresh(created, ["user_roles"])

    await AuditRepository(db).log(
        action=AuditAction.USER_REGISTERED,
        entity_type="user",
        entity_id=str(created.id),
        actor_id=created.id,
        metadata={"roles": role_names},
    )

    logger.info("User registered | id=%s email=%s roles=%s",
                created.id, created.email, role_names)

    return UserRead.model_validate(created)
