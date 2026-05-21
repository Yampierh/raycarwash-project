from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from domains.auth.service import create_session_and_tokens, get_current_user_for_onboarding
from domains.onboarding.orchestrator import OnboardingOrchestrator
from domains.users.models import User
from infrastructure.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/onboarding", tags=["Onboarding"])


class AdvanceRequest(BaseModel):
    action: str
    payload: dict = {}


class AdvanceResponse(BaseModel):
    status: str
    current_step: str | None = None
    completed: bool
    access_token: str | None = None
    refresh_token: str | None = None
    auth_state: dict | None = None


@router.post("/advance", response_model=AdvanceResponse)
async def advance_onboarding(
    body: AdvanceRequest,
    current_user: User = Depends(get_current_user_for_onboarding),
    db: AsyncSession = Depends(get_db),
) -> AdvanceResponse:
    orchestrator = OnboardingOrchestrator(db)
    state = await orchestrator.advance(
        user=current_user,
        action=body.action,
        payload=body.payload,
    )

    resp = AdvanceResponse(
        status=state.status,
        current_step=state.current_step,
        completed=state.completed,
    )

    if state.completed:
        from domains.auth.service import create_session_and_tokens
        access_token, refresh_token, _session = await create_session_and_tokens(
            user=current_user,
            db=db,
            ip_address=None,
            user_agent=None,
        )
        resp.access_token = access_token
        resp.refresh_token = refresh_token

        assigned_role = state.state_data.get("assigned_role", "client")
        resp.auth_state = {
            "type": "active",
            "step": state.state_data.get("_next_step"),
            "context": {"role": assigned_role},
        }

    await db.commit()
    return resp
