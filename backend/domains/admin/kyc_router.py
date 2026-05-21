from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.service import require_role
from domains.onboarding.orchestrator import OnboardingOrchestrator
from domains.users.models import User
from domains.users.repository import UserRepository
from infrastructure.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/kyc", tags=["Admin KYC"])


class KycRejectRequest(BaseModel):
    reason: str


class KycActionResponse(BaseModel):
    message: str
    status: str
    completed: bool
    current_step: str | None = None


@router.post("/{user_id}/approve", response_model=KycActionResponse)
async def admin_approve_kyc(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role("admin")),
) -> KycActionResponse:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user_id format.",
        )
    target = await UserRepository(db).get_by_id(uid)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    orchestrator = OnboardingOrchestrator(db)
    state = await orchestrator.advance_system(
        target_user=target,
        action="approve_kyc",
        payload={"admin_id": str(admin_user.id)},
    )
    await db.commit()

    return KycActionResponse(
        message="KYC approved.",
        status=state.status,
        completed=state.completed,
    )


@router.post("/{user_id}/reject", response_model=KycActionResponse)
async def admin_reject_kyc(
    user_id: str,
    body: KycRejectRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_role("admin")),
) -> KycActionResponse:
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user_id format.",
        )
    target = await UserRepository(db).get_by_id(uid)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    orchestrator = OnboardingOrchestrator(db)
    state = await orchestrator.advance_system(
        target_user=target,
        action="reject_kyc",
        payload={"admin_id": str(admin_user.id), "reason": body.reason},
    )
    await db.commit()

    return KycActionResponse(
        message="KYC rejected.",
        status=state.status,
        completed=state.completed,
        current_step=state.current_step,
    )
