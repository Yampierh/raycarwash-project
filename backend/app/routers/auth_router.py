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
    Token,
    UserRead,
    UserUpdate,
    VerifyRequest,
    VerifyResponse,
)
from app.services.auth import AuthService, _TOKEN_TYPE_REFRESH, get_current_user
from app.services.email_service import EmailService

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
    
    has_password = user.password_hash and user.password_hash not in ("", "$!unusable$!")
    has_google = bool(user.google_id)
    has_apple = bool(user.apple_id)
    
    if has_password:
        auth_method = "password"
        if has_google or has_apple:
            auth_method = "both"
        suggested = "login"
    elif has_google:
        auth_method = "google"
        suggested = "social_login"
    elif has_apple:
        auth_method = "apple"
        suggested = "social_login"
    else:
        auth_method = "password"  # fallback
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
    
    has_password = user.password_hash and user.password_hash not in ("", "$!unusable$!")
    has_google = bool(user.google_id)
    has_apple = bool(user.apple_id)
    
    auth_methods = []
    if has_password:
        auth_methods.append("password")
    if has_google:
        auth_methods.append("google")
    if has_apple:
        auth_methods.append("apple")
    
    if not auth_methods:
        auth_methods.append("password")
    
    if has_password:
        suggested = "login_password"
    elif has_google or has_apple:
        suggested = "login_social"
    else:
        suggested = "login_password"
    
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
    
    if body.password:
        auth_methods.append("password")
        user = await AuthService.authenticate_user(
            identifier=body.identifier,
            password=body.password,
            db=db,
        )
    elif body.access_token:
        try:
            if "google" in body.access_token.lower()[:20]:
                google_data = await AuthService.verify_google_token(body.access_token)
                user = await user_repo.get_by_google_id(google_data["user_id"])
            else:
                apple_payload = await AuthService.verify_apple_token(
                    body.access_token,
                    settings.APPLE_BUNDLE_ID,
                )
                user = await user_repo.get_by_apple_id(apple_payload["sub"])
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
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
    
    access_token = AuthService.create_access_token(user.id, user.primary_role)
    refresh_token = AuthService.create_refresh_token(user.id, user.primary_role)
    
    needs_completion = not user.full_name or (
        not user.phone_number and body.identifier_type == "email"
    )
    
    temp_token = None
    next_step = "app"
    
    if needs_completion:
        temp_token = AuthService.create_registration_token(user.id, user.primary_role)
        next_step = "complete_profile"
    
    if user.primary_role == "detailer" and not needs_completion:
        next_step = "detailer_onboarding"
    
    await AuditRepository(db).log(
        action=AuditAction.USER_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"ip": request.client.host if request.client else None},
    )
    
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
    request: Request,
    body: CompleteProfileRequest,
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    """
    Completa el perfil del usuario después del registro.
    
    Este endpoint requiere un temporary registration token (temp_token)
    que se obtiene de /auth/verify cuando es un nuevo usuario.
    """
    temp_token = request.headers.get("X-Temp-Token")
    if not temp_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing registration token.",
        )
    
    try:
        payload = AuthService.decode_token(temp_token, expected_type="registration")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired registration token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await UserRepository(db).get_by_id(user_id)
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
        user.primary_roles = [role]
    
    await db.flush()
    
    access_token = AuthService.create_access_token(user.id, user.primary_role)
    refresh_token = AuthService.create_refresh_token(user.id, user.primary_role)
    
    next_step = "app"
    if user.primary_role == "detailer":
        next_step = "detailer_onboarding"
    
    return VerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        is_new_user=False,
        temp_token=None,
        needs_profile_completion=False,
        next_step=next_step,
        assigned_role=user.primary_role,
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
    refresh_token = AuthService.create_refresh_token(user.id, user.primary_role)

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
        401: {"description": "Refresh token invalid or expired."},
        429: {"description": "Rate limit exceeded."},
    },
)
@limiter.limit("5/minute")
async def refresh_access_token(
    request: Request,                       # MUST be first param for slowapi
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Token rotation: each refresh token is single-use.
    The client must save both new tokens from the response.
    """
    # All imports are at module level — no inline imports needed.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token is invalid or has expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = AuthService.decode_token(refresh_token, expected_type=_TOKEN_TYPE_REFRESH)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise credentials_exception

    user = await UserRepository(db).get_by_id(user_id)

    if user is None or not user.is_active or user.is_deleted:
        raise credentials_exception

    new_access  = AuthService.create_access_token(user.id, user.primary_role)
    new_refresh = AuthService.create_refresh_token(user.id, user.primary_role)

    logger.info("Token refreshed | user_id=%s", user.id)

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
    )


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
    response_model=Token,
    summary="Login or register with a Google OAuth2 access token.",
    responses={
        400: {"description": "Token inválido o expirado."},
        401: {"description": "No se pudo verificar con Google."},
    },
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def google_login(
    request: Request,
    body: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Flujo:
      1. Verifica el access_token con la API de Google (tokeninfo).
      2. Extrae email + google_id (user_id en la respuesta de Google).
      3. Busca usuario por google_id → si existe, login normal.
      4. Si no, busca por email → si existe, vincula el google_id.
      5. Si tampoco, crea una cuenta nueva con role=client e is_verified=True.
      6. Devuelve access_token + refresh_token (idéntico a /auth/token).
    """
    # 1. Verificar con Google
    try:
        google_data = await AuthService.verify_google_token(body.access_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    google_id: str = google_data["user_id"]
    email: str     = google_data["email"].lower()

    user_repo  = UserRepository(db)
    audit_repo = AuditRepository(db)

    # 2. Buscar por google_id
    user = await user_repo.get_by_google_id(google_id)

    if user is None:
        # 3. Buscar por email (puede que ya tenga cuenta con password)
        user = await user_repo.get_by_email(email)

        if user is not None:
            # 4. Vincular google_id a cuenta existente
            user.google_id  = google_id
            user.is_verified = True
            await db.flush()
            logger.info("Google account linked | user_id=%s email=%s", user.id, email)
        else:
            # 5. Crear cuenta nueva con rol 'client'
            full_name: str = google_data.get("name") or email.split("@")[0]
            user = User(
                email=email,
                full_name=full_name,
                password_hash=AuthService.generate_unusable_password(),
                google_id=google_id,
                is_verified=True,
            )
            # Get 'client' role and assign
            role_result = await db.execute(
                select(Role).where(Role.name == "client")
            )
            client_role = role_result.scalar_one()
            user.primary_roles = [client_role]
            
            user = await user_repo.create(user)
            await audit_repo.log(
                action=AuditAction.USER_REGISTERED,
                entity_type="user",
                entity_id=str(user.id),
                actor_id=user.id,
                metadata={"provider": "google"},
            )
            logger.info("New user via Google | user_id=%s email=%s", user.id, email)

    if not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account is deactivated.",
        )

    access_token  = AuthService.create_access_token(user.id, user.primary_role)
    refresh_token = AuthService.create_refresh_token(user.id, user.primary_role)

    await audit_repo.log(
        action=AuditAction.USER_SOCIAL_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"provider": "google", "ip": request.client.host if request.client else None},
    )
    logger.info("Google login | user_id=%s", user.id)

    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


# ── POST /auth/apple  (Apple Sign In) ────────────────────────────── #

@router.post(
    "/apple",
    response_model=Token,
    summary="Login or register with an Apple Sign In identity token.",
    responses={
        400: {"description": "identity_token inválido o malformado."},
        401: {"description": "No se pudo verificar con Apple."},
    },
)
@limiter.limit(f"{settings.RATE_LIMIT_AUTH_PER_MINUTE}/minute")
async def apple_login(
    request: Request,
    body: AppleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    Flujo:
      1. Verifica identity_token con las claves públicas de Apple (JWKS).
      2. Extrae apple_id (sub) y email del payload.
         ⚠️  Apple solo incluye email en el PRIMER login. En los siguientes
         el frontend debe enviar full_name y el backend busca por apple_id.
      3. Busca por apple_id → si existe, login.
      4. Si no, busca por email → vincula apple_id.
      5. Si tampoco, crea cuenta nueva.
         El full_name del body se usa solo en el primer registro.
    """
    # 1. Verificar con Apple
    try:
        apple_payload = await AuthService.verify_apple_token(
            body.identity_token,
            settings.APPLE_BUNDLE_ID,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    apple_id: str       = apple_payload["sub"]
    email: str | None   = apple_payload.get("email", "").lower() or None

    user_repo  = UserRepository(db)
    audit_repo = AuditRepository(db)

    # 2. Buscar por apple_id
    user = await user_repo.get_by_apple_id(apple_id)

    if user is None:
        if email:
            # 3. Buscar por email
            user = await user_repo.get_by_email(email)

        if user is not None:
            # 4. Vincular apple_id
            user.apple_id   = apple_id
            user.is_verified = True
            await db.flush()
            logger.info("Apple account linked | user_id=%s", user.id)
        else:
            # 5. Crear cuenta nueva
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Apple did not provide an email in this token. "
                        "This happens on repeat sign-ins when the user has "
                        "already registered. Please try again."
                    ),
                )
            full_name = body.full_name or email.split("@")[0]
            user = User(
                email=email,
                full_name=full_name,
                password_hash=AuthService.generate_unusable_password(),
                apple_id=apple_id,
                is_verified=True,
            )
            # Get 'client' role and assign via UserRoleAssociation
            role_result = await db.execute(
                select(Role).where(Role.name == "client")
            )
            client_role = role_result.scalar_one()
            user = await user_repo.create(user)
            
            # Assign role via UserRoleAssociation
            user_role = UserRoleAssociation(
                user_id=user.id,
                role_id=client_role.id,
            )
            db.add(user_role)
            await db.commit()
            await audit_repo.log(
                action=AuditAction.USER_REGISTERED,
                entity_type="user",
                entity_id=str(user.id),
                actor_id=user.id,
                metadata={"provider": "apple"},
            )
            logger.info("New user via Apple | user_id=%s", user.id)

    if not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account is deactivated.",
        )

    access_token  = AuthService.create_access_token(user.id, user.primary_role)
    refresh_token = AuthService.create_refresh_token(user.id, user.primary_role)

    await audit_repo.log(
        action=AuditAction.USER_SOCIAL_LOGIN,
        entity_type="user",
        entity_id=str(user.id),
        actor_id=user.id,
        metadata={"provider": "apple", "ip": request.client.host if request.client else None},
    )
    logger.info("Apple login | user_id=%s", user.id)

    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


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

    TODO Sprint 5: integrar SendGrid/SES para envío real del email.
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
