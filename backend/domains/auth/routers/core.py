import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError as JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.limiter import limiter
from infrastructure.db.session import get_db
from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.auth.models import Role, UserRoleAssociation
from domains.auth.refresh_token_repository import RefreshTokenRepository
from domains.auth.schemas import (
    AuthState,
    AuthStateContext,
    CheckEmailRequest,
    CheckEmailResponse,
    CompleteProfileRequest,
    IdentifierRequest,
    IdentifierResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RegisterRequest,
    Token,
    VerifyRequest,
    VerifyResponse,
)
from domains.auth.service import AuthService, get_current_user, get_current_user_for_onboarding
from domains.auth.auth_provider_repository import AuthProviderRepository
from domains.providers.models import ProviderProfile
from domains.users.models import ClientProfile, OnboardingStatus, User
from domains.users.repository import UserRepository
from domains.users.schemas import UserRead, UserUpdate
from infrastructure.email.service import EmailService

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account. Returns an onboarding token to complete profile.",
    responses={
        409: {"description": "Email already registered."},
        422: {"description": "Validation error (password too short, invalid email)."},
    },
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    existing = await UserRepository(db).get_by_email(body.email)
    if existing is not None and not existing.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    new_user = User(
        email=body.email,
        password_hash=AuthService.hash_password(body.password),
        onboarding_status=OnboardingStatus.PENDING_PROFILE,
    )
    user = await UserRepository(db).create(new_user)

    await AuditRepository(db).log(
        action=AuditAction.USER_REGISTERED,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None, "flow": "register"},
    )
    await db.commit()

    try:
        verification_token = await AuthService.create_email_verification_token(user.id, db)
        verify_url = f"{settings.APP_BASE_URL}/auth/email/verify?token={verification_token}"
        await EmailService.send_email_verification(
            email=str(body.email),
            verify_url=verify_url,
        )
    except Exception:
        logger.exception("Failed to send verification email to %s — registration proceeds", body.email)

    onboarding_token = AuthService.create_onboarding_token(user.id)
    return LoginResponse(
        onboarding_token=onboarding_token,
        roles=[],
        onboarding_completed=False,
        next_step="complete_profile",
        auth_state=AuthService.build_auth_state(user, intent_role=body.intent_role),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate with email + password. Returns tokens or onboarding token.",
    responses={
        401: {"description": "Invalid credentials or account deactivated."},
        429: {"description": "Rate limit exceeded."},
    },
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    user = await AuthService.authenticate_user(
        email=body.email,
        password=body.password,
        db=db,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    if user is None:
        logger.warning(
            "Failed login | email=%s ip=%s",
            body.email[:80],
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await AuditRepository(db).log(
        action=AuditAction.USER_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None, "flow": "login"},
    )

    if not user.onboarding_completed:
        await db.commit()
        onboarding_token = AuthService.create_onboarding_token(user.id)
        return LoginResponse(
            onboarding_token=onboarding_token,
            roles=user.roles,
            onboarding_completed=False,
            next_step="complete_profile",
            auth_state=AuthService.build_auth_state(user),
        )

    role_name = user.primary_role or "client"
    access_token = AuthService.create_access_token(user.id, role_name, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, role_name, db)

    # Hotfix H3 — mark step-up window so the user can immediately hit
    # /users/me?include=security|sessions, /auth/two-fa/enroll, etc.
    # without a spurious step_up_required bounce.
    await AuthService.record_step_up_success(request, user, db, auth_method="password")

    await db.commit()

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        roles=user.roles,
        onboarding_completed=True,
        next_step="app",
        auth_state=AuthService.build_auth_state(user, role_name),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current refresh token (this device only).",
)
async def logout(
    body: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    repo = RefreshTokenRepository(db)
    token_record = await repo.get_by_raw(body.refresh_token)

    if token_record is None or token_record.user_id != current_user.id:
        return

    await repo.revoke_by_raw(body.refresh_token)
    await db.commit()


@router.post(
    "/check-email",
    response_model=CheckEmailResponse,
    summary="Check if an email is registered and return auth method.",
)
@limiter.limit("10/minute")
async def check_email_exists(
    request: Request,
    body: CheckEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> CheckEmailResponse:
    user = await UserRepository(db).get_by_email(body.email.lower().strip())

    if user is None or user.is_deleted or not user.is_active:
        return CheckEmailResponse(
            email=body.email.lower().strip(),
            exists=False,
            auth_method="none",
            suggested_action="register",
        )

    providers = await AuthProviderRepository(db).get_providers_for_user(user.id)
    provider_names = {p.provider for p in providers}

    has_password = bool(user.password_hash and user.password_hash not in ("", "$!unusable$!"))
    has_google = "google" in provider_names
    has_apple  = "apple"  in provider_names

    if has_password:
        auth_method = "both" if (has_google or has_apple) else "password"
        suggested = "login"
    elif has_google:
        auth_method = "google"
        suggested = "social_login"
    elif has_apple:
        auth_method = "apple"
        suggested = "social_login"
    else:
        auth_method = "password"
        suggested = "login"

    return CheckEmailResponse(
        email=body.email.lower().strip(),
        exists=True,
        auth_method=auth_method,
        suggested_action=suggested,
    )


@router.post(
    "/identify",
    response_model=IdentifierResponse,
    summary="Identify user by email or phone (Identifier-First Auth).",
)
@limiter.limit("10/minute")
async def identify_user(
    request: Request,
    body: IdentifierRequest,
    db: AsyncSession = Depends(get_db),
) -> IdentifierResponse:
    identifier = body.identifier.strip()

    if "@" in identifier and "." in identifier:
        id_type = "email"
        normalized = identifier.lower()
    elif identifier.startswith("+") or identifier.isdigit():
        id_type = "phone"
        normalized = identifier
    else:
        id_type = body.identifier_type or "email"
        normalized = identifier.lower()

    if id_type == "phone":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone-based login is not yet supported. Please use your email address.",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_identifier(normalized, id_type)

    if user is None or user.is_deleted or not user.is_active:
        return IdentifierResponse(
            identifier=normalized,
            identifier_type=id_type,
            exists=False,
            auth_methods=[],
            is_new_user=True,
            suggested_action="register",
        )

    providers = await AuthProviderRepository(db).get_providers_for_user(user.id)
    provider_names = {p.provider for p in providers}

    has_password = bool(user.password_hash and user.password_hash not in ("", "$!unusable$!"))
    has_google = "google" in provider_names
    has_apple  = "apple"  in provider_names

    auth_methods: list[str] = []
    if has_password:
        auth_methods.append("password")
    if has_google:
        auth_methods.append("google")
    if has_apple:
        auth_methods.append("apple")
    if not auth_methods:
        auth_methods.append("password")

    suggested = "login_password" if has_password else "login_social"

    return IdentifierResponse(
        identifier=normalized,
        identifier_type=id_type,
        exists=True,
        auth_methods=auth_methods,
        is_new_user=False,
        suggested_action=suggested,
    )


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify credentials in Identifier-First flow.",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def verify_credentials(
    request: Request,
    body: VerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    user = None

    if body.password:
        user = await AuthService.authenticate_user(
            email=body.identifier,
            password=body.password,
            db=db,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    elif body.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Social authentication is no longer supported in this endpoint. Use POST /auth/google or /auth/apple.",
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account is deactivated.",
        )

    needs_completion = not user.onboarding_completed

    if needs_completion:
        temp_token = AuthService.create_onboarding_token(user.id)
        await db.commit()
        return VerifyResponse(
            access_token=None,
            refresh_token=None,
            is_new_user=False,
            temp_token=temp_token,
            needs_profile_completion=True,
            next_step="complete_profile",
            assigned_role=user.primary_role,
        )

    _role         = user.primary_role or "client"
    refresh_token = await AuthService.create_refresh_token(user.id, _role, db)
    access_token  = AuthService.create_access_token(user.id, _role, token_version=getattr(user, "token_version", 1))

    next_step = "detailer_onboarding" if user.primary_role == "detailer" else "app"

    await AuditRepository(db).log(
        action=AuditAction.USER_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None},
    )
    # Hotfix H3 — identifier-first verify with password is a real auth
    # event (user just presented the credential). OAuth/passkey paths of
    # this endpoint already 400 above, so we only reach here on password.
    await AuthService.record_step_up_success(request, user, db, auth_method="password")
    await db.commit()

    return VerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        is_new_user=False,
        temp_token=None,
        needs_profile_completion=False,
        next_step=next_step,
        assigned_role=user.primary_role,
    )


@router.put(
    "/complete-profile",
    response_model=VerifyResponse,
    summary="Complete user profile after registration.",
)
async def complete_user_profile(
    body: CompleteProfileRequest,
    current_user: User = Depends(get_current_user_for_onboarding),
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    user = current_user
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    await db.refresh(user, attribute_names=["client_profile", "provider_profile", "user_roles"])

    if user.onboarding_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profile already completed. Role changes require a separate verification flow.",
        )

    if body.full_name:
        user.full_name = body.full_name
    if body.phone_number:
        user.phone_number = body.phone_number
        from app.core.security import update_user_phone_hash
        update_user_phone_hash(user, body.phone_number, settings.PHONE_LOOKUP_KEY)

    from domains.auth.schemas import SERVICE_TYPE_TO_ROLE

    _next_step_map = {"client": "app", "detailer": "detailer_onboarding"}

    if body.service_type:
        effective_role = SERVICE_TYPE_TO_ROLE[body.service_type]
    else:
        effective_role = "client"

    role_result = await db.execute(select(Role).where(Role.name == effective_role))
    role = role_result.scalar_one_or_none()

    if role:
        already_has_role = any(ur.role_id == role.id for ur in user.user_roles)
        if not already_has_role:
            db.add(UserRoleAssociation(user_id=user.id, role_id=role.id))

    if effective_role == "client" and not user.client_profile:
        db.add(ClientProfile(user_id=user.id))
    elif effective_role == "detailer" and not user.provider_profile:
        db.add(ProviderProfile(user_id=user.id))

    user.onboarding_status = "completed"

    await db.flush()

    access_token  = AuthService.create_access_token(user.id, effective_role, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, effective_role, db)

    next_step = _next_step_map.get(effective_role, "app")

    await db.commit()

    return VerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        is_new_user=False,
        temp_token=None,
        needs_profile_completion=False,
        next_step=next_step,
        assigned_role=effective_role,
        auth_state=AuthService.build_auth_state(user, effective_role, has_provider_profile=False),
    )


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 Password Flow (Swagger UI compatibility).",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """OAuth2 Password Flow (RFC 6749 §4.3). Prefer /auth/login for application use."""
    user = await AuthService.authenticate_user(
        email=form_data.username,
        password=form_data.password,
        db=db,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    if user is None:
        logger.warning(
            "Failed login | email=%s ip=%s",
            form_data.username[:80],
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_name     = user.primary_role or "client"
    access_token  = AuthService.create_access_token(user.id, role_name, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, role_name, db)

    await AuditRepository(db).log(
        action=AuditAction.USER_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None},
    )
    # Hotfix H3 — OAuth2 Password Flow is a real auth event (RFC 6749 §4.3).
    await AuthService.record_step_up_success(request, user, db, auth_method="password")

    logger.info("Login success | user_id=%s role=%s", user.id, role_name)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Exchange a refresh token for a new access + refresh token pair.",
)
@limiter.limit("5/minute")
async def refresh_access_token(
    request: Request,
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Single-use rotation with theft detection (RFC 6749 §10.4)."""
    new_access, new_refresh = await AuthService.rotate_refresh_token(refresh_token, db)
    logger.info("Token rotated")
    return Token(access_token=new_access, refresh_token=new_refresh, token_type="bearer")


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the authenticated user's profile.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "/state",
    response_model=AuthState,
    summary="Resolve the current auth state (accepts access OR onboarding token).",
)
async def get_auth_state(
    current_user: User = Depends(get_current_user_for_onboarding),
) -> AuthState:
    """
    Single source of truth for post-auth navigation. Frontend calls this on
    app launch and after any auth event to derive routing without local flags.
    """
    return AuthService.build_auth_state(current_user)


@router.put(
    "/update",
    response_model=UserRead,
    summary="Update the authenticated user's basic profile fields.",
)
async def update_user_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    fields: dict = {}
    if payload.full_name is not None:
        fields["full_name"] = payload.full_name
    if payload.phone_number is not None:
        fields["phone_number"] = payload.phone_number
        from app.core.security import update_user_phone_hash
        update_user_phone_hash(current_user, payload.phone_number, settings.PHONE_LOOKUP_KEY)

    if fields:
        current_user = await UserRepository(db).update(current_user, fields)

    return UserRead.model_validate(current_user)
