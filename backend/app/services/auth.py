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
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)
settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Token type discriminators — prevent cross-type token reuse.
_TOKEN_TYPE_ACCESS  = "access"
_TOKEN_TYPE_REFRESH = "refresh"
_TOKEN_TYPE_RESET   = "password_reset"
_TOKEN_TYPE_REGISTRATION = "registration"
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
    def create_refresh_token(
        subject: uuid.UUID,
        role_name: str,
    ) -> str:
        """
        Long-lived token (7 days default). Used ONLY at POST /auth/refresh.

        NEVER attach this to regular API requests — it must be stored
        separately in expo-secure-store and sent only to /auth/refresh.
        """
        return AuthService._build_token(
            subject=subject,
            role_name=role_name,
            token_type=_TOKEN_TYPE_REFRESH,
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )

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
    async def verify_google_token(access_token: str) -> dict:
        """
        Verify a Google OAuth2 access token via the tokeninfo endpoint.

        Returns the tokeninfo dict which includes:
          - user_id  : Google's stable user ID (use as google_id)
          - email    : verified email address
          - expires_in: seconds remaining

        Raises ValueError on any verification failure.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v1/tokeninfo",
                params={"access_token": access_token},
            )

        if resp.status_code != 200:
            raise ValueError("Google token is invalid or has expired.")

        data = resp.json()
        if "error" in data:
            desc = data.get("error_description", data["error"])
            raise ValueError(f"Google token error: {desc}")

        if not data.get("email"):
            raise ValueError("Google token does not include an email claim.")
        if not data.get("verified_email", False):
            raise ValueError("Google account email is not verified.")

        return data

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
) -> User:
    """
    Decode the Bearer access token and return the authenticated User.

    Validates:
      1. Signature + expiry (jose)
      2. Token type = "access" (prevents refresh token reuse)
      3. User still exists and is active (DB lookup)
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