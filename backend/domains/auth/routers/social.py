import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.limiter import limiter
from infrastructure.db.session import get_db
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.auth_provider_repository import AuthProviderRepository
from domains.auth.schemas import AppleLoginRequest, GoogleLoginRequest, SocialAuthResponse
from domains.auth.service import AuthService
from domains.users.models import User
from domains.users.repository import UserRepository

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/google",
    response_model=SocialAuthResponse,
    summary="Login or register via Google OAuth2 PKCE authorization code.",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def google_login(
    request: Request,
    body: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> SocialAuthResponse:
    if body.redirect_uri not in settings.GOOGLE_ALLOWED_REDIRECT_URIS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri not allowed.",
        )

    try:
        google_data = await AuthService.exchange_google_code(
            body.code, body.code_verifier, body.redirect_uri
        )
    except ValueError as exc:
        status_code = status.HTTP_403_FORBIDDEN if "not verified" in str(exc) else status.HTTP_401_UNAUTHORIZED
        raise HTTPException(status_code=status_code, detail=str(exc))

    uid:   str = google_data["uid"]
    email: str = google_data["email"]

    user_repo     = UserRepository(db)
    provider_repo = AuthProviderRepository(db)
    audit_repo    = AuditRepository(db)
    is_new_user   = False

    provider_row = await provider_repo.get_by_provider("google", uid)

    if provider_row is not None:
        user = await user_repo.get_by_id(provider_row.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    else:
        user = await user_repo.get_by_email(email)
        if user is not None:
            await provider_repo.create(user.id, "google", uid, email)
            user.is_verified = True
            await db.flush()
            logger.info("Google account linked | user_id=%s email=%s", user.id, email)
        else:
            full_name = google_data.get("name") or email.split("@")[0]
            user = User(
                email=email,
                full_name=full_name,
                password_hash=AuthService.generate_unusable_password(),
                is_verified=True,
            )
            user = await user_repo.create(user)
            await provider_repo.create(user.id, "google", uid, email)
            await audit_repo.log(
                action=AuditAction.USER_REGISTERED,
                entity_type="user",
                entity_id=str(user.id),
                actor_id=user.id,
                metadata={"provider": "google"},
            )
            is_new_user = True
            logger.info("New user via Google | user_id=%s email=%s", user.id, email)

    if not user.is_active or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account deactivated.")

    await audit_repo.log(
        action=AuditAction.USER_SOCIAL_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"provider": "google", "ip": request.client.host if request.client else None},
    )

    await db.refresh(user, attribute_names=["user_roles"])

    if not user.onboarding_completed:
        logger.info("Google login — onboarding required | user_id=%s", user.id)
        await db.commit()
        return SocialAuthResponse(
            is_new_user=True,
            onboarding_required=True,
            onboarding_token=AuthService.create_onboarding_token(user.id),
        )

    access_token  = AuthService.create_access_token(user.id, user.primary_role, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, user.primary_role, db)
    # Hotfix H3 — OAuth identity-token verification is a real auth event.
    await AuthService.record_step_up_success(request, user, db, auth_method="google")
    await db.commit()
    logger.info("Google login | user_id=%s role=%s", user.id, user.primary_role)
    return SocialAuthResponse(
        is_new_user=is_new_user,
        access_token=access_token,
        refresh_token=refresh_token,
        active_role=user.primary_role,
    )


@router.post(
    "/apple",
    response_model=SocialAuthResponse,
    summary="Login or register via Apple Sign In identity token.",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_login(
    request: Request,
    body: AppleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> SocialAuthResponse:
    try:
        apple_payload = await AuthService.verify_apple_token(
            body.identity_token,
            settings.APPLE_BUNDLE_ID,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    uid:   str       = apple_payload["sub"]
    email: str | None = (apple_payload.get("email") or "").lower() or None

    user_repo     = UserRepository(db)
    provider_repo = AuthProviderRepository(db)
    audit_repo    = AuditRepository(db)
    is_new_user   = False

    provider_row = await provider_repo.get_by_provider("apple", uid)

    if provider_row is not None:
        user = await user_repo.get_by_id(provider_row.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    else:
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Apple did not include an email in this token. "
                    "This happens on repeat sign-ins for unregistered accounts. "
                    "Please sign out of Apple ID and try again."
                ),
            )
        user = await user_repo.get_by_email(email)
        if user is not None:
            await provider_repo.create(user.id, "apple", uid, email)
            user.is_verified = True
            await db.flush()
            logger.info("Apple account linked | user_id=%s", user.id)
        else:
            full_name = body.full_name or email.split("@")[0]
            user = User(
                email=email,
                full_name=full_name,
                password_hash=AuthService.generate_unusable_password(),
                is_verified=True,
            )
            user = await user_repo.create(user)
            await provider_repo.create(user.id, "apple", uid, email)
            await audit_repo.log(
                action=AuditAction.USER_REGISTERED,
                entity_type="user",
                entity_id=str(user.id),
                actor_id=user.id,
                metadata={"provider": "apple"},
            )
            is_new_user = True
            logger.info("New user via Apple | user_id=%s", user.id)

    if not user.is_active or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account deactivated.")

    await audit_repo.log(
        action=AuditAction.USER_SOCIAL_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"provider": "apple", "ip": request.client.host if request.client else None},
    )

    await db.refresh(user, attribute_names=["user_roles"])

    if not user.onboarding_completed:
        logger.info("Apple login — onboarding required | user_id=%s", user.id)
        await db.commit()
        return SocialAuthResponse(
            is_new_user=True,
            onboarding_required=True,
            onboarding_token=AuthService.create_onboarding_token(user.id),
        )

    access_token  = AuthService.create_access_token(user.id, user.primary_role, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, user.primary_role, db)
    # Hotfix H3 — Apple ID token verification is a real auth event.
    await AuthService.record_step_up_success(request, user, db, auth_method="apple")
    await db.commit()
    logger.info("Apple login | user_id=%s role=%s", user.id, user.primary_role)
    return SocialAuthResponse(
        is_new_user=is_new_user,
        access_token=access_token,
        refresh_token=refresh_token,
        active_role=user.primary_role,
    )
