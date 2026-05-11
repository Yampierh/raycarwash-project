import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.limiter import limiter
from infrastructure.db.session import get_db
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.schemas import (
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetResponse,
)
from domains.auth.service import AuthService
from domains.users.repository import UserRepository
from infrastructure.email.service import EmailService

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/password-reset",
    response_model=PasswordResetResponse,
    summary="Request a password reset email.",
)
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetResponse:
    """
    Send a password reset email. Always returns 200 to prevent user enumeration.
    Token is single-use and DB-backed (SHA-256 hash only stored).
    """
    _SAFE_RESPONSE = PasswordResetResponse(message="If that email is registered, a reset link has been sent.")

    user = await UserRepository(db).get_by_email(str(body.email))

    if user is None or not user.is_active or user.is_deleted:
        return _SAFE_RESPONSE

    reset_token = await AuthService.create_password_reset_token(user.id, user.primary_role, db)
    reset_url   = f"{settings.APP_BASE_URL}/auth/password-reset/confirm?token={reset_token}"

    await EmailService.send_password_reset(
        email=str(body.email),
        reset_url=reset_url,
        full_name=user.full_name,
    )

    await AuditRepository(db).log(
        action=AuditAction.PASSWORD_RESET_REQUESTED,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None},
    )

    return _SAFE_RESPONSE


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetConfirmResponse,
    summary="Confirm password reset with single-use token",
)
@limiter.limit("5/minute")
async def confirm_password_reset(
    request: Request,
    body: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetConfirmResponse:
    """
    Verify the single-use reset token and update the user's password.
    Increments token_version to invalidate all existing sessions.
    """
    user_id = await AuthService.verify_password_reset_token(body.token, db)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or inactive.",
        )

    user.password_hash = AuthService.hash_password(body.new_password)
    user.token_version = getattr(user, "token_version", 1) + 1

    await db.commit()

    await AuditRepository(db).log(
        action=AuditAction.PASSWORD_RESET_REQUESTED,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None, "action": "password_changed"},
    )

    return PasswordResetConfirmResponse(
        message="Password reset successfully. Please log in with your new password.",
    )
