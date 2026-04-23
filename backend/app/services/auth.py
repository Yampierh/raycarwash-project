# app/services/auth.py  —  Sprint 3
#
# ADDITIONS vs Sprint 2:
#   - create_refresh_token()  → long-lived opaque refresh token stored
#     in the DB (RefreshToken model-less for MVP: encoded as a JWT with
#     a "type": "refresh" claim and longer TTL).
#   - verify_refresh_token()  → decode + validate a refresh JWT.
#
# WHY encode refresh tokens as JWTs (instead of random opaque tokens)?
#   PRO: stateless — no DB table needed for the MVP.
#   CON: cannot be individually revoked before expiry.
#
#   The trade-off is acceptable for Sprint 3 MVP because:
#     - Access tokens expire in 30 minutes (small blast radius).
#     - Refresh tokens expire in 7 days (longer, but revocable at
#       the account level by rotating SECRET_KEY — a nuclear option).
#
#   Sprint 4 upgrade path: swap to opaque tokens stored in a
#   `refresh_tokens` table with a revoked_at column.
#
# RBAC Changes (Sprint 6):
#   - role is now stored as a string (role name) in JWT payload
#   - User model uses has_role() method to check permissions
#   - require_role() accepts role names as strings

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)
settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Token type discriminators — prevent cross-type token reuse.
_TOKEN_TYPE_ACCESS       = "access"
_TOKEN_TYPE_REFRESH      = "refresh"
_TOKEN_TYPE_RESET        = "password_reset"
_TOKEN_TYPE_REGISTRATION = "registration"
_TOKEN_TYPE_ONBOARDING   = "onboarding"   # scope-limited: only /onboarding/* endpoints
_TOKEN_TYPE_WEBAUTHN_REG  = "webauthn_registration"
_TOKEN_TYPE_WEBAUTHN_AUTH = "webauthn_authentication"

# Expose constants for use in routers without breaking encapsulation
TOKEN_TYPE_WEBAUTHN_REG  = _TOKEN_TYPE_WEBAUTHN_REG
TOKEN_TYPE_WEBAUTHN_AUTH = _TOKEN_TYPE_WEBAUTHN_AUTH


class AuthService:

    # ---- Password -------------------------------------------------- #

    @staticmethod
    def hash_password(plain_password: str) -> str:
        return _pwd_context.hash(plain_password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return _pwd_context.verify(plain_password, hashed_password)

    # ---- Token creation -------------------------------------------- #

    @staticmethod
    def _build_token(
        subject: uuid.UUID,
        role_name: str,
        token_type: str,
        expires_delta: timedelta,
    ) -> str:
        now    = datetime.now(timezone.utc)
        expire = now + expires_delta
        payload = {
            "sub":  str(subject),
            "role": role_name,
            "type": token_type,          
            "iat":  int(now.timestamp()),
            "exp":  int(expire.timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def create_access_token(
        subject: uuid.UUID,
        role_name: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Short-lived token (30 min default). Attached to every API request."""
        return AuthService._build_token(
            subject=subject,
            role_name=role_name,
            token_type=_TOKEN_TYPE_ACCESS,
            expires_delta=expires_delta
            or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )

    @staticmethod
    async def create_refresh_token(
        subject: uuid.UUID,
        role_name: str,
        db: AsyncSession,
        family_id: uuid.UUID | None = None,
    ) -> str:
        """
        Issue a new refresh token and persist it in refresh_tokens.

        The raw token is returned once and never stored — only SHA-256(token)
        lives in the DB.  Pass an existing family_id during rotation to keep
        the same session group; omit it to start a new family.
        """
        raw = secrets.token_urlsafe(32)
        fid = family_id or uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await RefreshTokenRepository(db).create(
            user_id=subject,
            raw_token=raw,
            family_id=fid,
            expires_at=expires_at,
        )
        return raw

    @staticmethod
    def decode_token(token: str, expected_type: str = _TOKEN_TYPE_ACCESS) -> dict:
        """
        Decode and verify a JWT. Raises JWTError on any validation failure.

        The `expected_type` check prevents token type confusion:
        using a refresh token where an access token is expected is
        silently rejected.
        """
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != expected_type:
            raise JWTError(
                f"Wrong token type: expected '{expected_type}', "
                f"got '{payload.get('type')}'."
            )
        return payload

    # ---- Password reset token -------------------------------------- #

    @staticmethod
    def create_password_reset_token(user_id: uuid.UUID, role_name: str) -> str:
        """Short-lived token (1 h) sent inside a reset link. Type = 'password_reset'."""
        return AuthService._build_token(
            subject=user_id,
            role_name=role_name,
            token_type=_TOKEN_TYPE_RESET,
            expires_delta=timedelta(hours=1),
        )

    @staticmethod
    def create_registration_token(user_id: uuid.UUID, role_name: str) -> str:
        """
        Temporary token for completing profile after registration.
        Type = 'registration'. Valid for 30 minutes.
        Used in the Identifier-First auth flow.
        """
        return AuthService._build_token(
            subject=user_id,
            role_name=role_name,
            token_type=_TOKEN_TYPE_REGISTRATION,
            expires_delta=timedelta(minutes=30),
        )

    @staticmethod
    def create_webauthn_challenge_token(
        user_id: uuid.UUID,
        challenge_b64: str,
        ctype: str,
    ) -> str:
        """
        Embed a WebAuthn challenge in a short-lived signed JWT (5 min).

        This keeps challenge storage stateless — no extra DB table needed.
        The challenge bytes are base64url-encoded so they survive JSON serialization.

        Args:
            user_id:      UUID of the user who initiated the ceremony.
            challenge_b64: base64url-encoded random challenge bytes (32 bytes → 43 chars).
            ctype:         "webauthn_registration" or "webauthn_authentication".

        Returns:
            A signed JWT that the client echoes back in the /complete request.
        """
        if ctype not in (_TOKEN_TYPE_WEBAUTHN_REG, _TOKEN_TYPE_WEBAUTHN_AUTH):
            raise ValueError(f"Invalid webauthn ctype: {ctype!r}")

        now    = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.WEBAUTHN_CHALLENGE_EXPIRE_MINUTES)
        payload = {
            "sub":       str(user_id),
            "challenge": challenge_b64,
            "type":      ctype,
            "iat":       int(now.timestamp()),
            "exp":       int(expire.timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def decode_webauthn_challenge_token(
        token: str, expected_type: str
    ) -> tuple[uuid.UUID, bytes]:
        """
        Decode a WebAuthn challenge JWT and return (user_id, challenge_bytes).

        Raises:
            HTTPException 401 if the token is invalid, expired, or wrong type.
        """
        from webauthn.helpers import base64url_to_bytes

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired WebAuthn challenge token.",
            ) from exc

        if payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="WebAuthn challenge token type mismatch.",
            )

        try:
            user_id   = uuid.UUID(payload["sub"])
            challenge = base64url_to_bytes(payload["challenge"])
        except (KeyError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed WebAuthn challenge token.",
            ) from exc

        return user_id, challenge

    # ---- Social login helpers -------------------------------------- #

    @staticmethod
    def generate_unusable_password() -> str:
        """
        Returns a bcrypt hash of a cryptographically random secret.
        Social-login users are assigned this hash so the password
        field stays non-null but the hash can never be guessed or used.
        """
        return _pwd_context.hash(secrets.token_hex(32))

    @staticmethod
    def create_onboarding_token(user_id: uuid.UUID) -> str:
        """
        Scope-limited token (30 min) issued to users who authenticated via a
        social provider but have no roles assigned yet.

        The 'scope' claim is checked in get_current_user() — any endpoint
        that does NOT opt-in via allow_onboarding_scope=True will return 403.
        """
        now    = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=30)
        payload = {
            "sub":   str(user_id),
            "type":  _TOKEN_TYPE_ACCESS,
            "scope": _TOKEN_TYPE_ONBOARDING,
            "iat":   int(now.timestamp()),
            "exp":   int(expire.timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    async def rotate_refresh_token(
        raw_token: str,
        db: AsyncSession,
    ) -> tuple[str, str]:
        """
        Single-use refresh token rotation with theft detection.

        Returns (new_access_token, new_refresh_token) on success.
        Raises HTTPException 401 on any failure.
        Raises HTTPException 401 + revokes entire family if reuse is detected.
        """
        repo = RefreshTokenRepository(db)
        token_row = await repo.get_by_raw(raw_token)

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if token_row is None:
            raise credentials_exception

        # Theft detection: token already consumed or explicitly revoked
        if token_row.used_at is not None or token_row.revoked:
            await repo.revoke_family(token_row.family_id)
            logger.warning(
                "Refresh token reuse detected — family revoked | user_id=%s family=%s",
                token_row.user_id,
                token_row.family_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalidated. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if token_row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise credentials_exception

        # Consume this token and issue a new pair
        await repo.mark_used(token_row.id)

        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(token_row.user_id)
        if user is None or not user.is_active or user.is_deleted:
            raise credentials_exception

        new_access  = AuthService.create_access_token(user.id, user.primary_role or "client")
        new_refresh = await AuthService.create_refresh_token(
            user.id,
            user.primary_role or "client",
            db,
            family_id=token_row.family_id,
        )
        return new_access, new_refresh

    @staticmethod
    async def exchange_google_code(
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> dict:
        """
        Exchange a PKCE authorization code for Google tokens and extract
        the user's identity from the returned id_token.

        No client_secret is required — PKCE replaces it for public clients
        (mobile apps where the secret cannot be kept confidential).

        Returns:
            {"uid": str, "email": str, "name": str | None}

        Raises ValueError on any verification failure.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code":          code,
                    "client_id":     settings.GOOGLE_CLIENT_ID,
                    "code_verifier": code_verifier,
                    "redirect_uri":  redirect_uri,
                    "grant_type":    "authorization_code",
                },
            )

        if resp.status_code != 200:
            raise ValueError(f"Google token exchange failed: {resp.text}")

        token_data = resp.json()
        if "error" in token_data:
            raise ValueError(f"Google error: {token_data.get('error_description', token_data['error'])}")

        id_token_str = token_data.get("id_token")
        if not id_token_str:
            raise ValueError("Google response did not include an id_token.")

        # Verify id_token signature with Google's public keys
        async with httpx.AsyncClient(timeout=10.0) as client:
            certs_resp = await client.get("https://www.googleapis.com/oauth2/v3/certs")
        certs_resp.raise_for_status()
        jwks = certs_resp.json()

        try:
            header = jwt.get_unverified_header(id_token_str)
        except JWTError as exc:
            raise ValueError(f"Cannot parse Google id_token header: {exc}") from exc

        kid = header.get("kid")
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key is None:
            raise ValueError("No Google public key matches the token's 'kid'.")

        try:
            options = {"verify_aud": bool(settings.GOOGLE_CLIENT_ID)}
            payload = jwt.decode(
                id_token_str,
                key,
                algorithms=["RS256"],
                audience=settings.GOOGLE_CLIENT_ID or None,
                options=options,
            )
        except JWTError as exc:
            raise ValueError(f"Google id_token verification failed: {exc}") from exc

        if not payload.get("email_verified", False):
            raise ValueError("Google account email is not verified.")

        uid = payload.get("sub")
        if not uid:
            raise ValueError("Google id_token is missing the 'sub' claim.")

        return {
            "uid":   uid,
            "email": payload.get("email", "").lower(),
            "name":  payload.get("name"),
        }

    @staticmethod
    async def verify_apple_token(identity_token: str, bundle_id: str) -> dict:
        """
        Verify an Apple Sign In identity_token (RS256 JWT signed by Apple).

        Steps:
          1. Extract the 'kid' from the token header.
          2. Fetch Apple's public JWKS from appleid.apple.com.
          3. Decode + verify the JWT using the matching key.

        Returns the decoded payload which includes:
          - sub   : Apple's stable user ID (use as apple_id)
          - email : user's email (only present on first sign-in)
          - iss   : https://appleid.apple.com
          - aud   : your app's bundle ID

        Raises ValueError on any verification failure.
        """
        try:
            header = jwt.get_unverified_header(identity_token)
        except JWTError as exc:
            raise ValueError(f"Cannot parse Apple identity_token header: {exc}") from exc

        kid = header.get("kid")
        if not kid:
            raise ValueError("Apple identity_token is missing the 'kid' header.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get("https://appleid.apple.com/auth/keys")
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise ValueError(f"Could not fetch Apple JWKS: {exc}") from exc

        jwks = resp.json()
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key is None:
            raise ValueError("No Apple public key matches the token's 'kid'. Token may be stale.")

        try:
            # python-jose accepts a JWK dict directly as the key parameter.
            options = {"verify_aud": bool(bundle_id)}
            payload = jwt.decode(
                identity_token,
                key,
                algorithms=["RS256"],
                audience=bundle_id or None,
                issuer="https://appleid.apple.com",
                options=options,
            )
        except JWTError as exc:
            raise ValueError(f"Apple identity_token verification failed: {exc}") from exc

        if not payload.get("sub"):
            raise ValueError("Apple identity_token is missing the 'sub' claim.")

        return payload

    # ---- Authentication -------------------------------------------- #

    @staticmethod
    async def authenticate_user(
        email: str,
        password: str,
        db: AsyncSession,
    ) -> User | None:
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(email)

        if user is None:
            _pwd_context.dummy_verify()   # Timing-safe — prevent user enumeration
            return None

        if not user.is_active or user.is_deleted:
            return None

        if not AuthService.verify_password(password, user.password_hash):
            return None

        return user


# ------------------------------------------------------------------ #
#  FastAPI dependency: get_current_user                               #
# ------------------------------------------------------------------ #

async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    db:    Annotated[AsyncSession, Depends(get_db)],
    allow_onboarding_scope: bool = False,
) -> User:
    """
    Decode the Bearer access token and return the authenticated User.

    Validates:
      1. Signature + expiry (jose)
      2. Token type = "access" (prevents refresh token reuse)
      3. User still exists and is active (DB lookup)
      4. If scope == "onboarding" and allow_onboarding_scope is False → 403

    Endpoints that are part of the onboarding flow must inject this dependency
    with allow_onboarding_scope=True via a custom Depends wrapper.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = AuthService.decode_token(token, expected_type=_TOKEN_TYPE_ACCESS)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    # Scope check: onboarding tokens cannot access regular endpoints
    if payload.get("scope") == _TOKEN_TYPE_ONBOARDING and not allow_onboarding_scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Onboarding required. Complete role selection before accessing this endpoint.",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if user is None or not user.is_active or user.is_deleted:
        logger.warning("Auth failed — user inactive or missing: %s", user_id)
        raise credentials_exception

    # Eager load user_roles relationship for RBAC methods (is_client, is_detailer, etc.)
    await db.refresh(user, attribute_names=['user_roles'])
    for ur in user.user_roles:
        await db.refresh(ur, attribute_names=['role'])

    return user


async def get_current_user_for_onboarding(
    token: Annotated[str, Depends(_oauth2_scheme)],
    db:    Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Variant of get_current_user that accepts onboarding-scoped tokens.
    Use as Depends() on /onboarding/* and /auth/complete-profile endpoints.
    """
    return await get_current_user(token=token, db=db, allow_onboarding_scope=True)


# ------------------------------------------------------------------ #
#  WebSocket auth helper                                              #
# ------------------------------------------------------------------ #

async def ws_get_current_user(
    token: str,
    db: AsyncSession,
) -> User | None:
    """
    WebSocket-safe authentication.

    WebSocket connections cannot send HTTP headers after the handshake, so
    the JWT is passed as a query parameter (?token=<jwt>).

    Returns None instead of raising so the WS endpoint can close cleanly
    with an appropriate close code rather than an HTTP 401.
    """
    try:
        payload = AuthService.decode_token(token, expected_type=_TOKEN_TYPE_ACCESS)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            return None
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        return None

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if user is None or not user.is_active or user.is_deleted:
        return None

    await db.refresh(user, attribute_names=["user_roles"])
    for ur in user.user_roles:
        await db.refresh(ur, attribute_names=["role"])

    return user


# ------------------------------------------------------------------ #
#  RBAC dependency factory                                            #
# ------------------------------------------------------------------ #

def require_role(*role_names: str):
    """
    Usage:
        @router.post("/admin/resource")
        async def handler(_: User = Depends(require_role("admin"))):
    
    Or for multiple allowed roles:
        @router.get("/detailer-only")
        async def handler(_: User = Depends(require_role("detailer", "admin"))):
    """
    async def _dep(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if not any(current_user.has_role(name) for name in role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Requires one of: {list(role_names)}. "
                    f"Your roles: {list(current_user.roles)}."
                ),
            )
        return current_user
    return _dep