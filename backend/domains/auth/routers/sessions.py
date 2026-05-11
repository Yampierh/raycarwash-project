import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_db
from domains.auth.refresh_token_repository import RefreshTokenRepository
from domains.auth.schemas import SessionRead, SessionRevokeResponse, SessionsListResponse
from domains.auth.service import get_current_user
from domains.users.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get(
    "/sessions",
    response_model=SessionsListResponse,
    summary="List active sessions for current user",
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionsListResponse:
    """List all active sessions (refresh token families) for the current user."""
    repo = RefreshTokenRepository(db)
    tokens, total = await repo.get_sessions_for_user(current_user.id)

    sessions = [
        SessionRead(
            family_id=token.family_id,
            created_at=token.created_at,
            last_used_at=token.used_at,
            revoked=token.revoked,
            expires_at=token.expires_at,
        )
        for token in tokens
    ]

    return SessionsListResponse(sessions=sessions, total=total)


@router.delete(
    "/sessions/{family_id}",
    response_model=SessionRevokeResponse,
    summary="Revoke a specific session",
)
async def revoke_session(
    family_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionRevokeResponse:
    """Revoke a specific session by family ID (useful when a device is lost)."""
    repo = RefreshTokenRepository(db)

    session = await repo.get_session_by_family(current_user.id, family_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    await repo.revoke_session(current_user.id, family_id)
    await db.commit()

    return SessionRevokeResponse(
        revoked_family_id=family_id,
        message="Session revoked successfully.",
    )


@router.delete(
    "/sessions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke all sessions (log out everywhere)",
)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke all sessions for the current user (log out from all devices)."""
    repo = RefreshTokenRepository(db)
    await repo.revoke_all_for_user(current_user.id)
    await db.commit()
