import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.limiter import limiter
from infrastructure.db.session import get_db
from domains.auth.schemas import PasswordResetRequest
from domains.auth.service import AuthService
from domains.users.repository import UserRepository
from infrastructure.email.service import EmailService

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/email/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify email address with the token from the verification email.",
)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Mark the user's email as verified. Token is single-use and DB-backed (24h TTL).
    Idempotent — verifying an already-verified email returns 200.
    """
    user_id = await AuthService.verify_email_verification_token(token, db)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found.")

    if not user.is_verified:
        user.is_verified = True
        await db.commit()
        logger.info("Email verified | user=%s", user.id)

    return {"message": "Email address verified successfully."}


@router.post(
    "/email/resend-verification",
    status_code=status.HTTP_200_OK,
    summary="Resend the email verification link.",
)
@limiter.limit("3/minute")
async def resend_verification_email(
    request: Request,
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Re-send the email verification link. Always returns 200 to prevent enumeration.
    A new token invalidates any previously issued token for the user.
    """
    _SAFE = {"message": "If that email is registered and unverified, a new link has been sent."}

    user = await UserRepository(db).get_by_email(str(body.email))
    if user is None or not user.is_active or user.is_deleted or user.is_verified:
        return _SAFE

    verification_token = await AuthService.create_email_verification_token(user.id, db)
    verify_url = f"{settings.APP_BASE_URL}/auth/email/verify?token={verification_token}"
    await EmailService.send_email_verification(
        email=str(body.email),
        verify_url=verify_url,
        full_name=user.full_name,
    )
    logger.info("Email verification resent | user=%s", user.id)
    return _SAFE
