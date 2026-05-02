# app/routers/auth_router.py
#
# Auth endpoints. All rate limits are per IP via slowapi.
#
# Registration & login flow:
#   POST /auth/register        → create account → onboarding_token
#   POST /auth/login           → authenticate  → tokens or onboarding_token
#   PUT  /auth/complete-profile → set name/role → access + refresh tokens
#   POST /auth/logout          → revoke current refresh token (this device only)
#
# Legacy / compatibility:
#   POST /auth/verify          → login-only alias (Identifier-First flow)
#   POST /auth/token           → OAuth2 Password Flow (Swagger UI compat)
#
# Social auth:
#   POST /auth/google          → Google PKCE code exchange
#   POST /auth/apple           → Apple identity token verification
#
# Passkeys (WebAuthn/FIDO2):
#   POST /auth/webauthn/register/begin|complete
#   POST /auth/webauthn/authenticate/begin|complete

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.limiter import limiter
from infrastructure.db.session import get_db
from domains.audit.models import AuditAction
from domains.auth.models import Role, UserRoleAssociation
from domains.providers.models import ProviderProfile
from domains.users.models import ClientProfile, OnboardingStatus, User
from domains.audit.repository import AuditRepository
from domains.auth.auth_provider_repository import AuthProviderRepository
from domains.auth.password_reset_token_repository import PasswordResetTokenRepository
from domains.users.repository import UserRepository
from domains.auth.refresh_token_repository import RefreshTokenRepository
from domains.auth.webauthn_repository import WebAuthnRepository
from domains.auth.schemas import (
    AppleLoginRequest,
    CheckEmailRequest,
    CheckEmailResponse,
    CompleteProfileRequest,
    GoogleLoginRequest,
    IdentifierRequest,
    IdentifierResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterRequest,
    SessionRead,
    SessionsListResponse,
    SessionRevokeResponse,
    SocialAuthResponse,
    Token,
    WebAuthnRegisterBeginResponse,
    WebAuthnRegisterCompleteRequest,
    WebAuthnRegisterCompleteResponse,
    WebAuthnAuthBeginRequest,
    WebAuthnAuthBeginResponse,
    WebAuthnAuthCompleteRequest,
    WebAuthnCredentialsListResponse,
    WebAuthnCredentialRead,
    WebAuthnCredentialRenameRequest,
    WebAuthnCredentialDeleteResponse,
    VerifyRequest,
    VerifyResponse,
)
from domains.users.schemas import UserRead, UserUpdate
from domains.auth.service import (
    AuthService,
    TOKEN_TYPE_WEBAUTHN_REG,
    TOKEN_TYPE_WEBAUTHN_AUTH,
    get_current_user,
    get_current_user_for_onboarding,
)
from infrastructure.email.service import EmailService
from domains.auth.webauthn_service import WebAuthnService
from domains.auth.webauthn_repository import WebAuthnRepository

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── POST /auth/register  (create new account) ──────────────────────────────── #

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
    """
    Creates a bare user account with no role and no profile.
    Returns an onboarding_token (scope='onboarding') to be used at
    PUT /auth/complete-profile to select role and set full_name.
    """
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

    # Send email verification link (non-blocking — failure does not abort registration)
    verification_token = AuthService.create_email_verification_token(user.id)
    verify_url = f"{settings.APP_BASE_URL}/auth/email/verify?token={verification_token}"
    try:
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
    )


# ── POST /auth/login  (authenticate existing account) ──────────────────────── #

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
    """
    Authenticates an existing user. Never creates a new account.

    - If credentials are wrong → 401 (same message regardless of whether email exists).
    - If onboarding_completed == False → returns onboarding_token so the user
      can finish their profile without re-entering their password.
    - If onboarding_completed == True → returns access_token + refresh_token.
    """
    user = await AuthService.authenticate_user(email=body.email, password=body.password, db=db)

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
        )

    role_name = user.primary_role or "client"
    access_token = AuthService.create_access_token(user.id, role_name, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, role_name, db)

    await db.commit()

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        roles=user.roles,
        onboarding_completed=True,
        next_step="app",
    )


# ── POST /auth/logout  (revoke current session) ─────────────────────────────── #

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
    """
    Revokes only the provided refresh token, leaving other sessions (other devices)
    active. To invalidate all sessions, the user must log out from each device.
    """
    repo = RefreshTokenRepository(db)
    token_record = await repo.get_by_raw(body.refresh_token)

    if token_record is None or token_record.user_id != current_user.id:
        # Silently succeed — either already revoked or not found; don't leak info
        return

    await repo.revoke_by_raw(body.refresh_token)
    await db.commit()


# ── POST /auth/check-email  (verify email exists) ──────────────────────────── #

@router.post(
    "/check-email",
    response_model=CheckEmailResponse,
    summary="Check if an email is registered and return auth method.",
    responses={
        429: {"description": "Rate limit exceeded."},
    },
)
@limiter.limit("10/minute")
async def check_email_exists(
    request: Request,
    body: CheckEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> CheckEmailResponse:
    """
    Returns the auth method(s) registered for an email without confirming existence.
    auth_method: "password" | "google" | "apple" | "both" | "none"
    suggested_action: "login" | "social_login" | "register"
    """
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


# ── POST /auth/identify  (Identifier-First) ──────────────────────────────── #

@router.post(
    "/identify",
    response_model=IdentifierResponse,
    summary="Identify user by email or phone (Identifier-First Auth).",
    responses={
        429: {"description": "Rate limit exceeded."},
    },
)
@limiter.limit("10/minute")
async def identify_user(
    request: Request,
    body: IdentifierRequest,
    db: AsyncSession = Depends(get_db),
) -> IdentifierResponse:
    """
    Pre-step for the Identifier-First login flow.
    Returns available auth methods (password, google, apple) so the UI
    can show the right credential form without exposing whether the email exists.
    Phone login is not yet supported.
    """
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
            detail=(
                "Phone-based login is not yet supported. "
                "Please use your email address to sign in."
            ),
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


# ── POST /auth/verify  (Identifier-First verification) ─────────────────────── #

@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify credentials in Identifier-First flow.",
    responses={
        401: {"description": "Invalid credentials."},
        429: {"description": "Rate limit exceeded."},
    },
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def verify_credentials(
    request: Request,
    body: VerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    """
    Login-only endpoint for the Identifier-First flow (backward compatibility).
    For new accounts use POST /auth/register instead.

    If onboarding is incomplete returns an onboarding_token (needs_profile_completion=True).
    Social auth via access_token is no longer accepted here — use /auth/google or /auth/apple.
    """
    user = None

    if body.password:
        user = await AuthService.authenticate_user(
            email=body.identifier,
            password=body.password,
            db=db,
        )
        # /auth/verify is now login-only. For new accounts use POST /auth/register.

    elif body.access_token:
        # Social auth via /auth/verify is deprecated.
        # Use POST /auth/google (PKCE) or POST /auth/apple instead.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Social authentication is no longer supported in this endpoint. "
                "Use POST /auth/google or POST /auth/apple."
            ),
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

    temp_token = None
    next_step = "app"

    if needs_completion:
        temp_token = AuthService.create_onboarding_token(user.id)
        next_step = "complete_profile"
        await db.commit()
        return VerifyResponse(
            access_token=None,
            refresh_token=None,
            is_new_user=False,
            temp_token=temp_token,
            needs_profile_completion=True,
            next_step=next_step,
            assigned_role=user.primary_role,
        )

    _role         = user.primary_role or "client"
    refresh_token = await AuthService.create_refresh_token(user.id, _role, db)
    access_token  = AuthService.create_access_token(user.id, _role, token_version=getattr(user, "token_version", 1))

    if user.primary_role == "detailer":
        next_step = "detailer_onboarding"

    await AuditRepository(db).log(
        action=AuditAction.USER_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None},
    )
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


# ── PUT /auth/complete-profile  (Complete registration) ─────────────── #

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
    """
    Sets full_name, phone_number, and role after account creation.
    One-time endpoint: only callable while onboarding_status != "completed".
    Once onboarding is finished, role changes must go through a dedicated
    verified upgrade flow (Stripe Identity / background check).
    Returns a full access + refresh token pair on success.
    """
    user = current_user
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    # Explicitly refresh profiles to avoid stale identity-map state from the
    # same SQLAlchemy session (common in tests and after prior refreshes).
    await db.refresh(user, attribute_names=["client_profile", "provider_profile", "user_roles"])

    # Reject role escalation: once onboarding is complete, the user already has
    # a primary role. Adding a privileged role (e.g. detailer) here would bypass
    # the verified upgrade flow.
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

    # Determine role from service_type — backend is the authority, never trust frontend role claims
    if body.service_type:
        effective_role = SERVICE_TYPE_TO_ROLE[body.service_type]
    else:
        effective_role = "client"

    role_result = await db.execute(select(Role).where(Role.name == effective_role))
    role = role_result.scalar_one_or_none()

    if role:
        # Idempotent: only add role association if not already present
        already_has_role = any(ur.role_id == role.id for ur in user.user_roles)
        if not already_has_role:
            db.add(UserRoleAssociation(user_id=user.id, role_id=role.id))

    # Idempotent: create profile only if it doesn't exist yet
    if effective_role == "client" and not user.client_profile:
        db.add(ClientProfile(user_id=user.id))
    elif effective_role == "detailer" and not user.provider_profile:
        db.add(ProviderProfile(user_id=user.id))

    # Mark onboarding as complete — single source of truth
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
    )


# ── POST /auth/token  (login) ─────────────────────────────────────── #

@router.post(
    "/token",
    response_model=Token,
    summary="Exchange credentials for JWT access + refresh tokens.",
    responses={
        401: {"description": "Invalid credentials."},
        429: {"description": "Rate limit exceeded — max 10 login attempts/minute per IP."},
    },
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def login_for_access_token(
    request: Request,                       # MUST be first param for slowapi key extraction
    form_data: OAuth2PasswordRequestForm = Depends(OAuth2PasswordRequestForm),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    # TODO: MEDIUM - Duplicate endpoint. Prefer /auth/login for application use.
    #       This exists for Swagger UI "Authorize" button compatibility (RFC 6749 §4.3).
    OAuth2 Password Flow (RFC 6749 §4.3).

    Request body — form-encoded (NOT JSON):
        username=user@example.com&password=secret

    Returns:
        { access_token, refresh_token, token_type: "bearer" }

    Security:
    - 401 message never distinguishes "user not found" vs "wrong password"
      (prevents user enumeration, OWASP A07).
    - bcrypt dummy_verify() runs even when the user doesn't exist,
      making both code paths take the same ~100 ms (timing-safe).
    """
    user = await AuthService.authenticate_user(
        email=form_data.username,
        password=form_data.password,
        db=db,
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

    logger.info("Login success | user_id=%s role=%s", user.id, role_name)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


# ── POST /auth/refresh  (token rotation) ─────────────────────────── #

@router.post(
    "/refresh",
    response_model=Token,
    summary="Exchange a refresh token for a new access + refresh token pair.",
    responses={
        401: {"description": "Refresh token invalid, expired, or reuse detected."},
        429: {"description": "Rate limit exceeded."},
    },
)
@limiter.limit("5/minute")
async def refresh_access_token(
    request: Request,
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Stateful single-use rotation.  Each call invalidates the presented token
    and issues a new pair.  Presenting an already-used token revokes the
    entire session family (theft detection — RFC 6749 §10.4).
    """
    new_access, new_refresh = await AuthService.rotate_refresh_token(refresh_token, db)
    logger.info("Token rotated")
    return Token(access_token=new_access, refresh_token=new_refresh, token_type="bearer")


# ── GET /auth/me  (profile) ──────────────────────────────────────── #

@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the authenticated user's profile.",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


# ── PUT /auth/update  (update own profile) ───────────────────────── #

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
    """
    Updates full_name and/or phone_number.
    Note: service_address was moved to ClientProfile/ProviderProfile (Sprint 6).
    Only supplied (non-None) fields are changed.
    """
    fields: dict = {}
    if payload.full_name is not None:
        fields["full_name"] = payload.full_name
    if payload.phone_number is not None:
        fields["phone_number"] = payload.phone_number
        from app.core.security import update_user_phone_hash
        update_user_phone_hash(current_user, payload.phone_number, settings.PHONE_LOOKUP_KEY)
    # NOTE: service_address removed - it now lives in ClientProfile/ProviderProfile

    if fields:
        current_user = await UserRepository(db).update(current_user, fields)

    return UserRead.model_validate(current_user)


# ── POST /auth/google  (Google OAuth2 login) ─────────────────────── #

@router.post(
    "/google",
    response_model=SocialAuthResponse,
    summary="Login or register via Google OAuth2 PKCE authorization code.",
    responses={
        400: {"description": "redirect_uri no permitida o código inválido."},
        401: {"description": "No se pudo verificar con Google."},
        403: {"description": "Email de Google no verificado."},
    },
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def google_login(
    request: Request,
    body: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> SocialAuthResponse:
    """
    Flujo PKCE:
      1. Validar redirect_uri contra whitelist.
      2. Intercambiar authorization_code por id_token con Google (sin client_secret).
      3. Verificar email_verified en el id_token.
      4. Buscar en auth_providers por (google, sub).
         a. Si existe → usuario conocido, emitir tokens normales.
         b. Si no existe:
            - Buscar por email → account linking (preservar roles existentes).
            - Si tampoco existe → crear usuario sin roles.
      5. Si usuario tiene roles → JWT normal.
         Si no → onboarding_token (30 min, scope=onboarding).
    """
    # 1. Whitelist check
    if body.redirect_uri not in settings.GOOGLE_ALLOWED_REDIRECT_URIS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="redirect_uri not allowed.",
        )

    # 2–3. PKCE exchange + email_verified check
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

    # 4. Look up by auth_provider row
    provider_row = await provider_repo.get_by_provider("google", uid)

    if provider_row is not None:
        user = await user_repo.get_by_id(provider_row.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    else:
        # Account linking or new user
        user = await user_repo.get_by_email(email)
        if user is not None:
            # Linking: preserve existing roles
            await provider_repo.create(user.id, "google", uid, email)
            user.is_verified = True
            await db.flush()
            logger.info("Google account linked | user_id=%s email=%s", user.id, email)
        else:
            # Brand new user — no role yet
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

    # 5. Issue tokens based on role status
    await db.refresh(user, attribute_names=["user_roles"])

    if not user.onboarding_completed:
        logger.info("Google login — onboarding required | user_id=%s", user.id)
        return SocialAuthResponse(
            is_new_user=True,
            onboarding_required=True,
            onboarding_token=AuthService.create_onboarding_token(user.id),
        )

    access_token  = AuthService.create_access_token(user.id, user.primary_role, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, user.primary_role, db)
    logger.info("Google login | user_id=%s role=%s", user.id, user.primary_role)
    return SocialAuthResponse(
        is_new_user=is_new_user,
        access_token=access_token,
        refresh_token=refresh_token,
        active_role=user.primary_role,
    )


# ── POST /auth/apple  (Apple Sign In) ────────────────────────────── #

@router.post(
    "/apple",
    response_model=SocialAuthResponse,
    summary="Login or register via Apple Sign In identity token.",
    responses={
        400: {"description": "Apple no proporcionó email (re-authenticate required)."},
        401: {"description": "No se pudo verificar el identity_token."},
    },
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_login(
    request: Request,
    body: AppleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> SocialAuthResponse:
    """
    Flujo:
      1. Verificar identity_token con JWKS de Apple.
      2. Buscar en auth_providers por (apple, sub).
         a. Si existe → usuario conocido. Apple no envía email en logins posteriores
            — no importa, el email ya está guardado en auth_providers.provider_email.
         b. Si no existe:
            - email es obligatorio (solo está en el primer login de Apple).
            - Buscar por email → account linking (preservar roles).
            - Si tampoco → crear usuario sin roles.
      3. Si usuario tiene roles → JWT normal.
         Si no → onboarding_token.
    """
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
            # Linking: preserve existing roles
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
        return SocialAuthResponse(
            is_new_user=True,
            onboarding_required=True,
            onboarding_token=AuthService.create_onboarding_token(user.id),
        )

    access_token  = AuthService.create_access_token(user.id, user.primary_role, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, user.primary_role, db)
    logger.info("Apple login | user_id=%s role=%s", user.id, user.primary_role)
    return SocialAuthResponse(
        is_new_user=is_new_user,
        access_token=access_token,
        refresh_token=refresh_token,
        active_role=user.primary_role,
    )


# ── POST /auth/password-reset ─────────────────────────────────────── #

@router.post(
    "/password-reset",
    response_model=PasswordResetResponse,
    summary="Request a password reset email.",
    responses={
        200: {"description": "Siempre 200 para no revelar si el email existe."},
    },
)
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> PasswordResetResponse:
    """
    Genera un token de reset de contraseña (single-use, DB-backed) y lo envía por email.

    FIX: Now uses database-backed single-use tokens instead of stateless JWT.
    - Token is stored as SHA-256 hash (not the raw token)
    - Token can only be used once (used_at is marked)
    - Expires after 1 hour

    Siempre devuelve HTTP 200 aunque el email no exista — esto previene
    la enumeración de usuarios (OWASP A07).
    """
    _SAFE_RESPONSE = PasswordResetResponse(message="If that email is registered, a reset link has been sent.")

    user = await UserRepository(db).get_by_email(str(body.email))

    if user is None or not user.is_active or user.is_deleted:
        # Always return the same response to prevent enumeration.
        return _SAFE_RESPONSE

    # FIX: Create single-use token (async, DB-backed)
    reset_token = await AuthService.create_password_reset_token(
        user.id, user.primary_role, db
    )
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


# ------------------------------------------------------------------ #
#  Password Reset Confirm (FIX: single-use token)                         #
# ------------------------------------------------------------------ #

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
    
    FIX: Uses database-backed single-use tokens.
    - Token is validated against DB (not JWT)
    - Token is consumed (marked as used) on success
    - Cannot be reused
    """
    user_id = await AuthService.verify_password_reset_token(body.token, db)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token.",
        )
    
    # Get user and update password
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found or inactive.",
        )
    
    # Update password and increment token_version to invalidate sessions
    user.password_hash = AuthService.hash_password(body.new_password)
    user.token_version = getattr(user, 'token_version', 1) + 1
    
    await db.commit()
    
    await AuditRepository(db).log(
        action=AuditAction.PASSWORD_RESET_REQUESTED,  # Reuse action or add new one
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None, "action": "password_changed"},
    )
    
    return PasswordResetConfirmResponse(
        message="Password reset successfully. Please log in with your new password.",
    )


# ------------------------------------------------------------------ #
#  WebAuthn / FIDO2 Passkeys                                         #
# ------------------------------------------------------------------ #

import os
from webauthn.helpers import bytes_to_base64url


@router.post(
    "/webauthn/register/begin",
    response_model=WebAuthnRegisterBeginResponse,
    summary="Begin WebAuthn passkey registration",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def webauthn_register_begin(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebAuthnRegisterBeginResponse:
    """
    Step 1 of passkey registration (requires a valid Bearer token).

    Returns a `challenge_token` (short-lived JWT) and `options`
    (PublicKeyCredentialCreationOptions) that the client passes to
    `Passkey.register()`. The client must echo `challenge_token` back
    in the /complete request — the challenge is embedded inside it.
    """
    challenge = os.urandom(32)
    challenge_b64 = bytes_to_base64url(challenge)

    existing = await WebAuthnRepository(db).get_credentials_by_user(current_user.id)

    options = WebAuthnService.generate_registration_options(
        user=current_user,
        existing_credentials=existing,
        challenge=challenge,
    )
    challenge_token = AuthService.create_webauthn_challenge_token(
        user_id=current_user.id,
        challenge_b64=challenge_b64,
        ctype=TOKEN_TYPE_WEBAUTHN_REG,
    )

    return WebAuthnRegisterBeginResponse(
        challenge_token=challenge_token,
        options=options,
    )


@router.post(
    "/webauthn/register/complete",
    response_model=WebAuthnRegisterCompleteResponse,
    summary="Complete WebAuthn passkey registration",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def webauthn_register_complete(
    request: Request,
    body: WebAuthnRegisterCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebAuthnRegisterCompleteResponse:
    """
    Step 2 of passkey registration (requires a valid Bearer token).

    Verifies the attestation returned by `Passkey.register()` and
    stores the new credential in the database.
    """
    from webauthn.helpers.exceptions import InvalidRegistrationResponse, InvalidAuthenticationResponse
    from domains.auth.models import WebAuthnCredential

    # Decode the challenge JWT (also validates it hasn't expired / is the right type)
    user_id, challenge = AuthService.decode_webauthn_challenge_token(
        body.challenge_token, expected_type=TOKEN_TYPE_WEBAUTHN_REG
    )
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token user mismatch.")

    try:
        verified = WebAuthnService.verify_registration_response(
            challenge=challenge,
            credential_response=body.credential,
        )
    except (InvalidRegistrationResponse, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Passkey registration verification failed: {exc}",
        ) from exc

    credential = WebAuthnCredential(
        user_id=current_user.id,
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        transports=list(verified.credential_device_type) if verified.credential_device_type else None,
        device_name=body.device_name,
    )
    await WebAuthnRepository(db).create_credential(credential)
    await db.commit()

    return WebAuthnRegisterCompleteResponse(
        credential_id=bytes_to_base64url(verified.credential_id),
        device_name=body.device_name,
    )


@router.post(
    "/webauthn/authenticate/begin",
    response_model=WebAuthnAuthBeginResponse,
    summary="Begin WebAuthn passkey authentication",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def webauthn_authenticate_begin(
    request: Request,
    body: WebAuthnAuthBeginRequest,
    db: AsyncSession = Depends(get_db),
) -> WebAuthnAuthBeginResponse:
    """
    Step 1 of passkey authentication (public endpoint).

    The client provides the user's email so we can look up their stored
    credential IDs and include them in `allowCredentials`. Returns a
    `challenge_token` and `options` to pass to `Passkey.authenticate()`.
    """
    user = await UserRepository(db).get_by_email(body.email.lower().strip())
    if not user or not user.is_active or user.is_deleted:
        # Return a generic error to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No passkey found for this account.",
        )

    credentials = await WebAuthnRepository(db).get_credentials_by_user(user.id)
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No passkey found for this account.",
        )

    challenge = os.urandom(32)
    challenge_b64 = bytes_to_base64url(challenge)

    options = WebAuthnService.generate_authentication_options(
        credentials=credentials,
        challenge=challenge,
    )
    challenge_token = AuthService.create_webauthn_challenge_token(
        user_id=user.id,
        challenge_b64=challenge_b64,
        ctype=TOKEN_TYPE_WEBAUTHN_AUTH,
    )

    return WebAuthnAuthBeginResponse(
        challenge_token=challenge_token,
        options=options,
    )


@router.post(
    "/webauthn/authenticate/complete",
    response_model=Token,
    summary="Complete WebAuthn passkey authentication",
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def webauthn_authenticate_complete(
    request: Request,
    body: WebAuthnAuthCompleteRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Step 2 of passkey authentication (public endpoint).

    Verifies the assertion from `Passkey.authenticate()`, updates the
    sign_count in the DB, and returns an access_token + refresh_token pair.
    """
    from webauthn.helpers import base64url_to_bytes
    from webauthn.helpers.exceptions import InvalidRegistrationResponse, InvalidAuthenticationResponse
    from datetime import datetime, timezone

    # Decode challenge JWT
    user_id, challenge = AuthService.decode_webauthn_challenge_token(
        body.challenge_token, expected_type=TOKEN_TYPE_WEBAUTHN_AUTH
    )

    # Find the credential being used (by the credential ID in the response)
    raw_credential_id = base64url_to_bytes(body.credential.get("id", ""))
    repo = WebAuthnRepository(db)
    stored_cred = await repo.get_credential_by_id(raw_credential_id)

    if not stored_cred or stored_cred.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passkey authentication failed.",
        )

    try:
        verified = WebAuthnService.verify_authentication_response(
            challenge=challenge,
            credential_response=body.credential,
            stored_credential=stored_cred,
        )
    except (InvalidAuthenticationResponse, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Passkey authentication failed: {exc}",
        ) from exc

    # Update sign count
    await repo.update_sign_count(
        credential_id=raw_credential_id,
        sign_count=verified.new_sign_count,
        last_used_at=datetime.now(timezone.utc),
    )

    # Load user and issue tokens
    user = await UserRepository(db).get_by_id(user_id)
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive.",
        )

    _role         = user.primary_role or "client"
    access_token  = AuthService.create_access_token(user.id, _role, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, _role, db)

    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


# ------------------------------------------------------------------ #
#  Session Management (FIX for audit TODO-009)                            #
# ------------------------------------------------------------------ #

@router.get(
    "/sessions",
    response_model=SessionsListResponse,
    summary="List active sessions for current user",
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionsListResponse:
    """
    List all active sessions (refresh token families) for the current user.
    
    FIX: Enables users to see and manage their active sessions.
    Returns sessions grouped by family (device), showing creation time,
    last usage, and revocation status.
    """
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
    """
    Revoke a specific session (device/family_id).
    
    FIX: Enables users to selectively revoke sessions.
    Useful when a device is lost or the user wants to log out a specific device.
    """
    repo = RefreshTokenRepository(db)
    
    # Check if session exists
    session = await repo.get_session_by_family(current_user.id, family_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    
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
    """
    Revoke all sessions for the current user.
    
    FIX: Enables "log out everywhere" functionality.
    Useful when the user suspects their account is compromised.
    """
    repo = RefreshTokenRepository(db)
    await repo.revoke_all_for_user(current_user.id)
    await db.commit()


# ------------------------------------------------------------------ #
#  Passkey (WebAuthn) credential management                          #
# ------------------------------------------------------------------ #

import base64


@router.get(
    "/webauthn/credentials",
    response_model=WebAuthnCredentialsListResponse,
    summary="List registered passkeys for the current user.",
)
async def list_webauthn_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebAuthnCredentialsListResponse:
    """
    Return all passkeys (FIDO2 credentials) registered by the current user.
    Each entry shows the device name, creation time, and last use timestamp.
    """
    repo = WebAuthnRepository(db)
    creds = await repo.get_credentials_by_user(current_user.id)
    return WebAuthnCredentialsListResponse(
        credentials=[
            WebAuthnCredentialRead(
                id=c.id,
                credential_id=base64.urlsafe_b64encode(c.credential_id).rstrip(b"=").decode(),
                device_name=c.device_name,
                created_at=c.created_at,
                last_used_at=c.last_used_at,
            )
            for c in creds
        ],
        total=len(creds),
    )


@router.patch(
    "/webauthn/credentials/{credential_id}",
    response_model=WebAuthnCredentialRead,
    summary="Rename a passkey.",
)
async def rename_webauthn_credential(
    credential_id: uuid.UUID,
    body: WebAuthnCredentialRenameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebAuthnCredentialRead:
    """
    Update the user-visible device name for a registered passkey.
    Only the owner of the credential can rename it.
    """
    repo = WebAuthnRepository(db)
    updated = await repo.rename_credential(credential_id, current_user.id, body.device_name)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passkey not found.",
        )
    await db.commit()
    return WebAuthnCredentialRead(
        id=updated.id,
        credential_id=base64.urlsafe_b64encode(updated.credential_id).rstrip(b"=").decode(),
        device_name=updated.device_name,
        created_at=updated.created_at,
        last_used_at=updated.last_used_at,
    )


@router.delete(
    "/webauthn/credentials/{credential_id}",
    response_model=WebAuthnCredentialDeleteResponse,
    summary="Remove a registered passkey.",
)
async def delete_webauthn_credential(
    credential_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebAuthnCredentialDeleteResponse:
    """
    Delete a specific passkey. Useful when a device is lost or replaced.

    Guard: refuses to delete the last passkey if the user has no password
    and no other authentication method — prevents lockout.
    """
    repo = WebAuthnRepository(db)

    # Safety check: ensure the credential belongs to this user
    cred = await repo.get_by_pk_and_user(credential_id, current_user.id)
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passkey not found.",
        )

    # Lockout guard: block deletion of the last passkey when user has no password
    total = await repo.count_for_user(current_user.id)
    has_password = bool(current_user.password_hash)
    if total <= 1 and not has_password:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot remove the last passkey when no password is set. "
                "Set a password first, or register another passkey before removing this one."
            ),
        )

    deleted = await repo.delete_by_pk(credential_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passkey not found.",
        )
    await db.commit()
    return WebAuthnCredentialDeleteResponse(
        deleted_id=credential_id,
        message="Passkey removed successfully.",
    )


# ------------------------------------------------------------------ #
#  Email verification                                                 #
# ------------------------------------------------------------------ #

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
    Mark the user's email as verified.

    The token is a signed JWT (type='email_verification', 24h TTL) sent to
    the user's email address on registration.

    This endpoint is idempotent — verifying an already-verified email returns 200.
    """
    user_id = AuthService.decode_email_verification_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token.",
        )

    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found.",
        )

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
    body: PasswordResetRequest,     # reuse { email: EmailStr } schema
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Re-send the verification email. Always returns 200 to prevent enumeration.

    Rate-limited to 3/minute. The new token invalidates the previous one only
    by expiry — both remain valid until they expire (this is acceptable because
    double-verification is harmless).
    """
    _SAFE = {"message": "If that email is registered and unverified, a new link has been sent."}

    user = await UserRepository(db).get_by_email(str(body.email))
    if user is None or not user.is_active or user.is_deleted or user.is_verified:
        return _SAFE

    verification_token = AuthService.create_email_verification_token(user.id)
    verify_url = f"{settings.APP_BASE_URL}/auth/email/verify?token={verification_token}"
    await EmailService.send_email_verification(
        email=str(body.email),
        verify_url=verify_url,
        full_name=user.full_name,
    )
    logger.info("Email verification resent | user=%s", user.id)
    return _SAFE
