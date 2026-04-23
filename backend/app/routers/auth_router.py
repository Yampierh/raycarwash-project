# app/routers/auth_router.py  —  Sprint 4
#
# CHANGES vs Sprint 3:
#   - Rate limiting applied to POST /auth/token via slowapi.
#     10 requests/minute per IP prevents brute-force credential stuffing.
#   - Rate limiting applied to POST /auth/refresh (5/minute — less critical
#     but still protects against token-rotation abuse).

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import AuditAction, User, Role, UserRoleAssociation
from app.repositories.audit_repository import AuditRepository
from app.repositories.auth_provider_repository import AuthProviderRepository
from app.repositories.user_repository import UserRepository
from app.schemas.schemas import (
    AppleLoginRequest,
    CheckEmailRequest,
    CheckEmailResponse,
    CompleteProfileRequest,
    GoogleLoginRequest,
    IdentifierRequest,
    IdentifierResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    SocialAuthResponse,
    Token,
    UserRead,
    UserUpdate,
    VerifyRequest,
    VerifyResponse,
    WebAuthnRegisterBeginResponse,
    WebAuthnRegisterCompleteRequest,
    WebAuthnRegisterCompleteResponse,
    WebAuthnAuthBeginRequest,
    WebAuthnAuthBeginResponse,
    WebAuthnAuthCompleteRequest,
)
from app.services.auth import (
    AuthService,
    TOKEN_TYPE_WEBAUTHN_REG,
    TOKEN_TYPE_WEBAUTHN_AUTH,
    get_current_user,
    get_current_user_for_onboarding,
)
from app.services.email_service import EmailService
from app.services.webauthn_service import WebAuthnService
from app.repositories.webauthn_repository import WebAuthnRepository

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    Verifica si un email existe en la base de datos.
    
    Retorna el método de autenticación para permitir el flujo de login/register:
    - "password": existe con contraseña
    - "google": solo registrado con Google
    - "apple": solo registrado con Apple
    - "both": registrado con password + social
    
    suggested_action:
    - "login": mostrar campo contraseña
    - "social_login": mostrar opción de red social
    - "register": ir a registro
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
    Identifica al usuario por email o teléfono para el flujo Identifier-First.
    
    Flujo:
    1. Normaliza el identificador (email -> lowercase, phone -> E.164)
    2. Detecta el tipo si no se provee
    3. Busca en la base de datos
    4. Retorna los métodos de autenticación disponibles
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
    Verifica credenciales en el flujo Identifier-First.
    
    Puede verificar por:
    - password: Contraseña del usuario
    - access_token: Token de Google/Apple
    - otp_code: Código OTP (futuro)
    
    Si es nuevo usuario, genera un token temporal para completar perfil.
    """
    user_repo = UserRepository(db)
    auth_methods: list[str] = []
    user = None
    is_new_user = False

    if body.password:
        auth_methods.append("password")
        user = await AuthService.authenticate_user(
            email=body.identifier,
            password=body.password,
            db=db,
        )

        # ── New-user registration path ──────────────────────────────────────
        # If authenticate_user returned None, the user may not exist yet.
        # Check explicitly: if the email is truly new, create the account
        # with the supplied password and flag it for profile completion.
        if user is None:
            existing = await user_repo.get_by_email(body.identifier.lower().strip())
            if existing is not None:
                # User exists but password is wrong → real "Invalid credentials"
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Validate password length before creating the account
            if len(body.password) < 8:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Password must be at least 8 characters.",
                )
            # Create skeleton account — profile completion required
            new_user = User(
                email=body.identifier.lower().strip(),
                password_hash=AuthService.hash_password(body.password),
            )
            user = await user_repo.create(new_user)

            # Assign default role
            role_name = "client"
            role_result = await db.execute(select(Role).where(Role.name == role_name))
            role = role_result.scalar_one_or_none()
            if role:
                db.add(UserRoleAssociation(user_id=user.id, role_id=role.id))
                await db.flush()

            await AuditRepository(db).log(
                action=AuditAction.USER_REGISTERED,
                entity_type="user",
                entity_id=str(user.id),
                actor_id=user.id,
                metadata={"ip": request.client.host if request.client else None, "flow": "identifier_first"},
            )
            is_new_user = True

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
    
    refresh_token = await AuthService.create_refresh_token(user.id, user.primary_role, db)
    access_token  = AuthService.create_access_token(user.id, user.primary_role)

    # New accounts always need profile completion (no full_name yet)
    needs_completion = is_new_user or not user.full_name or (
        not user.phone_number and body.identifier_type == "email"
    )

    temp_token = None
    next_step = "app"

    if needs_completion:
        temp_token = AuthService.create_onboarding_token(user.id)
        next_step = "complete_profile"

    if user.primary_role == "detailer" and not needs_completion:
        next_step = "detailer_onboarding"
    
    if not is_new_user:
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
        is_new_user=needs_completion,
        temp_token=temp_token,
        needs_profile_completion=needs_completion,
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
    Completa el perfil del usuario después del registro.

    Requiere un Bearer token con scope='onboarding' (emitido por /auth/verify
    para usuarios nuevos por email/password, o por /auth/google / /auth/apple
    para usuarios sociales sin rol asignado).
    """
    user = current_user
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )
    
    if body.full_name:
        user.full_name = body.full_name
    if body.phone_number:
        user.phone_number = body.phone_number
    
    role_result = await db.execute(
        select(Role).where(Role.name == body.role)
    )
    role = role_result.scalar_one_or_none()
    if role:
        # Clear existing role assignments and set the new one via ORM association
        for existing in list(user.user_roles):
            await db.delete(existing)
        db.add(UserRoleAssociation(user_id=user.id, role_id=role.id))

    await db.flush()

    # Use body.role directly — user.primary_role reads from the stale in-memory
    # user_roles list and won't reflect the role we just added until a DB refresh.
    effective_role = body.role if role else (user.primary_role or "client")

    access_token  = AuthService.create_access_token(user.id, effective_role)
    refresh_token = await AuthService.create_refresh_token(user.id, effective_role, db)

    next_step = "detailer_onboarding" if effective_role == "detailer" else "app"

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

    access_token  = AuthService.create_access_token(user.id, user.primary_role)
    refresh_token = await AuthService.create_refresh_token(user.id, user.primary_role, db)

    await AuditRepository(db).log(
        action=AuditAction.USER_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None},
    )

    logger.info("Login success | user_id=%s role=%s", user.id, user.primary_role)

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
    Note: service_address was moved to ClientProfile/DetailerProfile (Sprint 6).
    Only supplied (non-None) fields are changed.
    """
    fields: dict = {}
    if payload.full_name is not None:
        fields["full_name"] = payload.full_name
    if payload.phone_number is not None:
        fields["phone_number"] = payload.phone_number
    # NOTE: service_address removed - it now lives in ClientProfile/DetailerProfile

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
    for ur in user.user_roles:
        await db.refresh(ur, attribute_names=["role"])

    if not user.user_roles:
        logger.info("Google login — onboarding required | user_id=%s", user.id)
        return SocialAuthResponse(
            is_new_user=True,
            onboarding_required=True,
            onboarding_token=AuthService.create_onboarding_token(user.id),
        )

    access_token  = AuthService.create_access_token(user.id, user.primary_role)
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
    for ur in user.user_roles:
        await db.refresh(ur, attribute_names=["role"])

    if not user.user_roles:
        logger.info("Apple login — onboarding required | user_id=%s", user.id)
        return SocialAuthResponse(
            is_new_user=True,
            onboarding_required=True,
            onboarding_token=AuthService.create_onboarding_token(user.id),
        )

    access_token  = AuthService.create_access_token(user.id, user.primary_role)
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
    Genera un token de reset de contraseña de 1 hora y lo envía por email.

    Siempre devuelve HTTP 200 aunque el email no exista — esto previene
    la enumeración de usuarios (OWASP A07).

    El token es un JWT de tipo 'password_reset'. El frontend debe dirigir
    al usuario a la pantalla de nueva contraseña con el token como parámetro.

    El envío real de email (SendGrid/SES) requiere configurar SMTP_ENABLED=True en .env.
    """
    _SAFE_RESPONSE = PasswordResetResponse(message="If that email is registered, a reset link has been sent.")

    user = await UserRepository(db).get_by_email(str(body.email))

    if user is None or not user.is_active or user.is_deleted:
        # Always return the same response to prevent enumeration.
        return _SAFE_RESPONSE

    reset_token = AuthService.create_password_reset_token(user.id, user.primary_role)
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
    from app.models.models import WebAuthnCredential

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

    await db.commit()

    return Token(
        access_token=AuthService.create_access_token(user.id, user.primary_role),
        refresh_token=AuthService.create_refresh_token(user.id, user.primary_role),
        token_type="bearer",
    )
