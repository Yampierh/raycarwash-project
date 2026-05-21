from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated

import httpx
import jwt
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
)
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError as JWTError
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from infrastructure.db.session import get_db
from domains.users.models import User
from domains.auth.refresh_token_repository import RefreshTokenRepository
from domains.users.repository import UserRepository
from domains.auth.models import UserLoginHistory

logger = logging.getLogger(__name__)
settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Token type discriminators — prevent cross-type token reuse.
_TOKEN_TYPE_ACCESS       = "access"
_TOKEN_TYPE_REFRESH      = "refresh"
_TOKEN_TYPE_RESET        = "password_reset"
_TOKEN_TYPE_REGISTRATION = "registration"
_TOKEN_TYPE_ONBOARDING   = "onboarding"
_TOKEN_TYPE_WEBAUTHN_REG   = "webauthn_registration"
_TOKEN_TYPE_WEBAUTHN_AUTH  = "webauthn_authentication"
_TOKEN_TYPE_EMAIL_VERIFY   = "email_verification"

TOKEN_TYPE_WEBAUTHN_REG  = _TOKEN_TYPE_WEBAUTHN_REG
TOKEN_TYPE_WEBAUTHN_AUTH = _TOKEN_TYPE_WEBAUTHN_AUTH


@lru_cache(maxsize=1)
def _get_private_key():
    """Cached RSA private key object — loaded once from settings."""
    s = get_settings()
    return load_pem_private_key(s.JWT_PRIVATE_KEY.encode(), password=None)


@lru_cache(maxsize=1)
def _get_public_key():
    """Cached RSA public key object — loaded once from settings."""
    s = get_settings()
    return load_pem_public_key(s.JWT_PUBLIC_KEY.encode())


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
        token_version: int = 1,
        session_id: uuid.UUID | None = None,
    ) -> str:
        now    = datetime.now(timezone.utc)
        expire = now + expires_delta
        payload = {
            "iss": settings.APP_BASE_URL,
            "aud": "raycarwash-api",
            "jti": str(uuid.uuid4()),
            "sub": str(subject),
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "role": role_name,
            "type": token_type,
            "v":    token_version,
        }
        # Plan 23 Fase 1 día 3: stateful session pointer. Only emit when
        # provided — we never serialize "sid": null so old verifiers can
        # ignore the claim without parsing surprises.
        if session_id is not None:
            payload["sid"] = str(session_id)
        return jwt.encode(payload, _get_private_key(), algorithm="RS256")

    @staticmethod
    def create_access_token(
        subject: uuid.UUID,
        role_name: str,
        token_version: int = 1,
        expires_delta: timedelta | None = None,
        session_id: uuid.UUID | None = None,
    ) -> str:
        """Short-lived token (30 min default). Attached to every API request."""
        return AuthService._build_token(
            subject=subject,
            role_name=role_name,
            token_type=_TOKEN_TYPE_ACCESS,
            token_version=token_version,
            session_id=session_id,
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
        Decode and verify a JWT signed with RS256.

        Validates:
          - Signature (RSA public key)
          - Expiry (exp claim)
          - Audience (aud == "raycarwash-api")
          - Token type (type claim must match expected_type)

        Raises JWTError on any validation failure.
        """
        payload = jwt.decode(
            token,
            _get_public_key(),
            algorithms=["RS256"],
            audience="raycarwash-api",
        )
        if payload.get("type") != expected_type:
            raise JWTError(
                f"Wrong token type: expected '{expected_type}', "
                f"got '{payload.get('type')}'."
            )
        return payload

    # ---- Password reset token -------------------------------------- #

    @staticmethod
    async def create_password_reset_token(
        user_id: uuid.UUID,
        role_name: str,
        db: AsyncSession,
    ) -> str:
        """
        Create a single-use password reset token and store its hash in DB.
        The raw token is returned to the user; only the hash is stored.
        """
        from domains.auth.password_reset_token_repository import PasswordResetTokenRepository

        raw = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        repo = PasswordResetTokenRepository(db)
        await repo.invalidate_all_for_user(user_id)
        await repo.create(user_id=user_id, raw_token=raw, expires_at=expires_at)

        return raw

    @staticmethod
    async def verify_password_reset_token(
        raw_token: str,
        db: AsyncSession,
    ) -> uuid.UUID | None:
        """
        Verify a password reset token and return user_id if valid.
        Single-use — token is consumed on verification.
        """
        from domains.auth.password_reset_token_repository import PasswordResetTokenRepository

        repo = PasswordResetTokenRepository(db)
        token = await repo.consume(raw_token)

        if token is None:
            return None

        return token.user_id

    @staticmethod
    def create_registration_token(user_id: uuid.UUID, role_name: str) -> str:
        """Temporary token for completing profile after registration. Valid 30 min."""
        return AuthService._build_token(
            subject=user_id,
            role_name=role_name,
            token_type=_TOKEN_TYPE_REGISTRATION,
            expires_delta=timedelta(minutes=30),
        )

    # ---- WebAuthn challenge tokens (kept for reference during Redis migration) #

    @staticmethod
    def decode_webauthn_challenge_token(
        token: str, expected_type: str
    ) -> tuple[uuid.UUID, bytes]:
        """
        Decode a WebAuthn challenge JWT and return (user_id, challenge_bytes).
        Raises HTTPException 401 if the token is invalid, expired, or wrong type.
        """
        from webauthn.helpers import base64url_to_bytes

        try:
            payload = jwt.decode(
                token,
                _get_public_key(),
                algorithms=["RS256"],
                options={"verify_aud": False},
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
        """Bcrypt hash of a random secret — for social-only accounts."""
        return _pwd_context.hash(secrets.token_hex(32))

    @staticmethod
    def create_onboarding_token(user_id: uuid.UUID) -> str:
        """
        Scope-limited token issued after registration/login before profile completion.
        type="onboarding" — rejected by all endpoints except /auth/complete-profile.
        """
        now    = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.ONBOARDING_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub":   str(user_id),
            "type":  _TOKEN_TYPE_ONBOARDING,
            "iat":   int(now.timestamp()),
            "exp":   int(expire.timestamp()),
        }
        return jwt.encode(payload, _get_private_key(), algorithm="RS256")

    @staticmethod
    def build_auth_state(
        user: "User",
        effective_role: str | None = None,
        has_provider_profile: bool | None = None,
        intent_role: str | None = None,
    ) -> "AuthState":
        """
        Derive a structured AuthState from existing user data.

        provider_profiles are loaded via lazy="selectin" on every authenticated
        request, so `user.provider_profile_for(DETAILER) is not None` is
        reliable when has_provider_profile is None. E1.B turned the
        relationship into 1:N; for the auth-state probe we look specifically
        at the DETAILER row because that's the vertical whose onboarding
        flow is wired to the "detailer_setup" step in the frontend.

        intent_role: declared intent during registration ("detailer" → step
        "provider_type" so the frontend asks for service type before profile).
        """
        from domains.auth.schemas import AuthState, AuthStateContext
        from domains.providers.models import ProviderType

        if not user.onboarding_completed:
            step = "provider_type" if intent_role == "detailer" else "profile_creation"
            return AuthState(
                type="onboarding",
                step=step,
                context=AuthStateContext(role=intent_role),
            )

        role = effective_role or user.primary_role or "client"

        if role == "detailer":
            if has_provider_profile is None:
                has_provider_profile = user.provider_profile_for(ProviderType.DETAILER) is not None
            step = None if has_provider_profile else "detailer_setup"
        else:
            step = None

        return AuthState(
            type="active",
            step=step,
            context=AuthStateContext(role=role),
        )

    @staticmethod
    async def create_email_verification_token(
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> str:
        """
        Create a single-use email verification token stored in DB.
        Returns the raw token to embed in the verification link.
        """
        from domains.auth.email_verification_token_repository import EmailVerificationTokenRepository

        raw = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS)

        repo = EmailVerificationTokenRepository(db)
        await repo.invalidate_all_for_user(user_id)
        await repo.create(user_id=user_id, raw_token=raw, expires_at=expires_at)

        return raw

    @staticmethod
    async def verify_email_verification_token(
        raw_token: str,
        db: AsyncSession,
    ) -> uuid.UUID | None:
        """
        Consume an email verification token and return user_id if valid.
        Returns None if token is invalid, used, or expired.
        """
        from domains.auth.email_verification_token_repository import EmailVerificationTokenRepository

        repo = EmailVerificationTokenRepository(db)
        token = await repo.consume(raw_token)

        if token is None:
            return None

        return token.user_id

    @staticmethod
    async def exchange_google_code(
        code: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> dict:
        """
        Exchange a PKCE authorization code for Google tokens and extract
        the user's identity from the returned id_token.

        Returns: {"uid": str, "email": str, "name": str | None}
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

        async with httpx.AsyncClient(timeout=10.0) as client:
            certs_resp = await client.get("https://www.googleapis.com/oauth2/v3/certs")
        certs_resp.raise_for_status()
        jwks = certs_resp.json()

        try:
            header = jwt.get_unverified_header(id_token_str)
        except JWTError as exc:
            raise ValueError(f"Cannot parse Google id_token header: {exc}") from exc

        kid = header.get("kid")
        key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key_data is None:
            raise ValueError("No Google public key matches the token's 'kid'.")

        try:
            from jwt.algorithms import RSAAlgorithm
            google_public_key = RSAAlgorithm.from_jwk(key_data)
            options = {"verify_aud": bool(settings.GOOGLE_CLIENT_ID)}
            payload = jwt.decode(
                id_token_str,
                google_public_key,
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
        Returns the decoded payload. Raises ValueError on any verification failure.
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
        key_data = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key_data is None:
            raise ValueError("No Apple public key matches the token's 'kid'. Token may be stale.")

        try:
            from jwt.algorithms import RSAAlgorithm
            apple_public_key = RSAAlgorithm.from_jwk(key_data)
            options = {"verify_aud": bool(bundle_id)}
            payload = jwt.decode(
                identity_token,
                apple_public_key,
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

    _LOCKOUT_THRESHOLD  = 5
    _LOCKOUT_MINUTES    = 15

    @staticmethod
    async def authenticate_user(
        email: str,
        password: str,
        db: AsyncSession,
        ip_address: str | None = None,
        user_agent: str | None = None,
        auth_method: str = "password",
    ) -> User | None:
        """
        Authenticate with email + password.

        Security properties:
          - Timing-safe: dummy_verify() always runs on missing user.
          - Brute-force protection: 5 consecutive failures → 15-min lockout.
          - Lockout resets automatically when locked_until expires.
          - Successful login resets failed_login_attempts to 0.
        Returns User on success, None on any failure.
        """
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(email)

        if user is None:
            _pwd_context.dummy_verify()
            return None

        if not user.is_active or user.is_deleted:
            _pwd_context.dummy_verify()
            await AuthService._record_login_attempt(
                db, None, ip_address, user_agent, auth_method, False, "account_inactive"
            )
            return None

        if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            _pwd_context.dummy_verify()
            logger.info("Login blocked — email not verified | user=%s", user.id)
            await AuthService._record_login_attempt(
                db, user.id, ip_address, user_agent, auth_method, False, "email_not_verified"
            )
            return None

        if user.is_locked:
            _pwd_context.dummy_verify()
            logger.warning(
                "Login rejected — account locked | user=%s locked_until=%s",
                user.id, user.locked_until,
            )
            await AuthService._record_login_attempt(
                db, user.id, ip_address, user_agent, auth_method, False, "account_locked"
            )
            return None

        if not AuthService.verify_password(password, user.password_hash):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            failure_reason = "invalid_password"
            if user.failed_login_attempts >= AuthService._LOCKOUT_THRESHOLD:
                user.locked_until = (
                    datetime.now(timezone.utc)
                    + timedelta(minutes=AuthService._LOCKOUT_MINUTES)
                )
                failure_reason = "account_locked"
                logger.warning(
                    "Account locked after %d failed attempts | user=%s locked_until=%s",
                    user.failed_login_attempts, user.id, user.locked_until,
                )
            await db.commit()
            await AuthService._record_login_attempt(
                db, user.id, ip_address, user_agent, auth_method, False, failure_reason
            )
            return None

        if user.failed_login_attempts:
            user.failed_login_attempts = 0
            user.locked_until = None
            await db.flush()

        await AuthService._record_login_attempt(
            db, user.id, ip_address, user_agent, auth_method, True
        )

        return user

    @staticmethod
    async def _record_login_attempt(
        db: AsyncSession,
        user_id: uuid.UUID | None,
        ip_address: str | None,
        user_agent: str | None,
        auth_method: str,
        was_successful: bool,
        failure_reason: str | None = None,
    ) -> None:
        """Record login attempt to user_login_history table."""
        if user_id is None:
            return
        entry = UserLoginHistory(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            auth_method=auth_method,
            was_successful=was_successful,
            failure_reason=failure_reason,
        )
        db.add(entry)
        try:
            await db.flush()
        except Exception:
            pass

    @staticmethod
    async def record_step_up_success(
        request,
        user: User,
        db: AsyncSession,
        *,
        auth_method: str,
    ) -> None:
        """Mark a fresh authentication event for both step-up and audit (hotfix H3).

        Call this at every site that proves the user just demonstrated
        possession of a credential — password, OAuth ID token, passkey,
        TOTP code, or current-password during a sensitive operation. Two
        invariants kept here so individual call sites can't forget one:

          1. Bump ``last_step_up_at`` (Redis primary + DB fallback) so
             ``require_step_up`` lets the user through for the next
             ``STEP_UP_TTL_MINUTES`` window.
          2. Record a successful login in ``user_login_history`` with the
             provided ``auth_method`` and the IP/UA already on the request.

        DO NOT call from ``/auth/refresh`` — refresh is "still
        authenticated", not "re-authenticated". Calling step-up there would
        let stolen refresh tokens bypass step-up walls indefinitely.

        Imports ``mark_step_up`` lazily to avoid a module-level cycle with
        ``app.core.step_up``, which depends on ``get_current_user`` from
        this module.
        """
        from app.core.step_up import mark_step_up

        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        await AuthService._record_login_attempt(
            db,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            auth_method=auth_method,
            was_successful=True,
        )
        await mark_step_up(request, user, db)

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

        # Atomic claim — exactly one concurrent rotation wins. Losers see
        # rowcount=0 and MUST treat it like reuse: revoke family + 401.
        claimed = await repo.mark_used_atomic(token_row.id)
        if not claimed:
            await repo.revoke_family(token_row.family_id)
            logger.warning(
                "Refresh rotation race lost — family revoked | user_id=%s family=%s",
                token_row.user_id,
                token_row.family_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Concurrent refresh detected. Please log in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(token_row.user_id)
        if user is None or not user.is_active or user.is_deleted:
            raise credentials_exception

        # Phase 6 / ADR-003: prefer active_role when set so /auth/refresh
        # preserves whichever role the user last switched to. Falls back to
        # primary_role for single-role users that never touched the
        # switcher.
        effective_role = user.active_role or user.primary_role or "client"

        # Plan 23 Fase 1 día 3 — same family = same session. Look up the
        # existing Session row, refresh its last_active_at, and mint the
        # new access token with the existing `sid`. No new Session row.
        from domains.auth.session_repository import SessionRepository
        session = await SessionRepository(db).get_by_family(token_row.family_id)
        sid_for_token = session.id if session else None
        if session is not None:
            await SessionRepository(db).update_last_active(session.id)

        new_access  = AuthService.create_access_token(
            user.id,
            effective_role,
            token_version=getattr(user, "token_version", 1),
            session_id=sid_for_token,
        )
        new_refresh = await AuthService.create_refresh_token(
            user.id,
            effective_role,
            db,
            family_id=token_row.family_id,
        )
        return new_access, new_refresh


# ------------------------------------------------------------------ #
#  Session cache + transactional create_session_and_tokens            #
#  (Plan 23 Fase 1 día 2-3)                                           #
# ------------------------------------------------------------------ #


from pydantic import BaseModel  # noqa: E402  — keep import local to this block


class SessionCacheSchema(BaseModel):
    """Minimal session data for auth validation.

    Cached in Redis with TTL=AUTH_SESSION_CACHE_TTL_SECONDS so the hot
    path of every authenticated request never pays a DB round-trip.
    Invalidated on revoke / IP change / logout via
    `invalidate_session_cache`.
    """
    id: uuid.UUID
    user_id: uuid.UUID
    revoked: bool
    last_active_at: datetime


def _session_cache_key(sid: str) -> str:
    return f"session:{sid}"


def _session_throttle_key(sid: str) -> str:
    return f"session:last_seen:{sid}"


async def get_session_cached(
    sid: str,
    db: AsyncSession,
    redis=None,
) -> SessionCacheSchema | None:
    """Read-through cache for stateful session validation.

    Returns None if the session doesn't exist. The caller is responsible
    for treating `revoked=True` as a 401 — we still return the row so it
    can be logged."""
    from domains.auth.session_repository import SessionRepository  # local — avoid cycles

    try:
        session_uuid = uuid.UUID(sid)
    except (ValueError, TypeError):
        return None

    if redis is not None:
        try:
            cached = await redis.get(_session_cache_key(sid))
            if cached:
                return SessionCacheSchema.model_validate_json(cached)
        except Exception as exc:  # cache failure → graceful fall-through to DB
            logger.warning("Session cache lookup failed (%s) — falling back to DB", exc)

    session = await SessionRepository(db).get_by_id(session_uuid)
    if session is None:
        return None

    payload = SessionCacheSchema(
        id=session.id,
        user_id=session.user_id,
        revoked=session.revoked,
        last_active_at=session.last_active_at,
    )
    if redis is not None:
        try:
            await redis.setex(
                _session_cache_key(sid),
                settings.AUTH_SESSION_CACHE_TTL_SECONDS,
                payload.model_dump_json(),
            )
        except Exception as exc:
            logger.warning("Session cache write failed (%s) — continuing", exc)
    return payload


async def invalidate_session_cache(sid: str, redis=None) -> None:
    """Drop the cached session row + the last-seen throttle marker. Safe
    to call when redis is None (e.g. test fixtures without Redis)."""
    if redis is None:
        return
    try:
        await redis.delete(_session_cache_key(sid))
        await redis.delete(_session_throttle_key(sid))
    except Exception as exc:
        logger.warning("Session cache invalidate failed (%s)", exc)


# ------------------------------------------------------------------ #
#  AuthService.create_session_and_tokens (Plan 23 Fase 1 día 3)       #
# ------------------------------------------------------------------ #


async def create_session_and_tokens(
    user: User,
    db: AsyncSession,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
    device_name: str | None = None,
    device_type: str | None = None,
) -> tuple[str, str, "Session"]:
    """Mint a refresh-token family, a Session row pointing at it, and an
    access token carrying the `sid` claim. Single point of entry for the
    login flow so we never end up with a half-written session.

    Returns (access_token, raw_refresh_token, session). Caller commits.
    """
    from domains.auth.session_repository import SessionRepository
    from domains.auth.models import Session  # noqa: F401  — re-export for type hints
    from infrastructure.auth.device_parser import parse_device_name, parse_device_type

    # Plan 23 Fase 2 día 1 — derive device label/type from UA when caller
    # didn't provide them. Frontend may also send `x-device-name` for a
    # nicer label (parser is the fallback).
    if device_name is None:
        device_name = parse_device_name(user_agent)
    if device_type is None:
        device_type = parse_device_type(user_agent)

    # 1. Refresh token → family_id.
    raw = secrets.token_urlsafe(32)
    family_id = uuid.uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    await RefreshTokenRepository(db).create(
        user_id=user.id,
        raw_token=raw,
        family_id=family_id,
        expires_at=expires_at,
    )

    # 2. Session row pinned to that family.
    session = await SessionRepository(db).create(
        user_id=user.id,
        family_id=family_id,
        device_name=device_name,
        device_type=device_type,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # 3. Access token with sid pointing at the session row.
    role_name = (
        user.primary_role
        if hasattr(user, "primary_role") and user.primary_role
        else "client"
    )
    access = AuthService.create_access_token(
        subject=user.id,
        role_name=role_name,
        token_version=getattr(user, "token_version", 1),
        session_id=session.id,
    )

    return access, raw, session


# ------------------------------------------------------------------ #
#  FastAPI dependency: get_current_user                               #
# ------------------------------------------------------------------ #


from infrastructure.redis.client import get_redis  # noqa: E402


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)],
    db:    Annotated[AsyncSession, Depends(get_db)],
    redis = Depends(get_redis),
    allow_onboarding_scope: bool = False,
) -> User:
    """
    Decode the Bearer token and return the authenticated User.

    Validates:
      1. RS256 signature + expiry + audience (via AuthService.decode_token)
      2. Token type = "access" (or "onboarding" when allow_onboarding_scope=True)
      3. User exists, is active, and is not deleted
      4. token_version claim "v" matches user.token_version (instant revocation)
      5. Onboarding is complete (unless token type is "onboarding")
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # First attempt to decode as access token; fall back to onboarding if allowed.
    payload = None
    token_type = None

    try:
        payload = AuthService.decode_token(token, expected_type=_TOKEN_TYPE_ACCESS)
        token_type = _TOKEN_TYPE_ACCESS
    except JWTError:
        try:
            payload = jwt.decode(
                token,
                _get_public_key(),
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
            if payload.get("type") != _TOKEN_TYPE_ONBOARDING:
                raise credentials_exception
            token_type = _TOKEN_TYPE_ONBOARDING
        except JWTError:
            raise credentials_exception

    try:
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    if token_type == _TOKEN_TYPE_ONBOARDING and not allow_onboarding_scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Onboarding required. Complete role selection before accessing this endpoint.",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if user is None or not user.is_active or user.is_deleted:
        logger.warning("Auth failed — user inactive or missing: %s", user_id)
        raise credentials_exception

    if token_type == _TOKEN_TYPE_ACCESS:
        token_v = payload.get("v")
        db_v    = getattr(user, "token_version", 1)
        if token_v is not None and token_v != db_v:
            logger.warning(
                "Auth rejected — token_version mismatch (token=%s db=%s) user=%s",
                token_v, db_v, user_id,
            )
            raise credentials_exception

        # Plan 23 Fase 1 día 3 — stateful session enforcement.
        # Backwards compatible: tokens minted before this rollout have no
        # `sid` claim, and the enforce flag stays False until the FE has
        # rotated. When enabled, we validate against the cached session
        # row and 401 on revoke.
        sid = payload.get("sid")
        if settings.AUTH_ENFORCE_SESSION and sid:
            if redis is None:
                logger.warning(
                    "AUTH_ENFORCE_SESSION enabled but Redis unavailable — "
                    "falling back to direct DB lookup for sid=%s", sid,
                )
            session = await get_session_cached(sid, db, redis)
            if session is None:
                logger.warning("Auth rejected — session not found sid=%s user=%s", sid, user_id)
                raise credentials_exception
            if session.revoked:
                logger.warning("Auth rejected — session revoked sid=%s user=%s", sid, user_id)
                raise credentials_exception
            if session.user_id != user.id:
                logger.warning(
                    "Auth rejected — session/user mismatch sid=%s session.user=%s token.user=%s",
                    sid, session.user_id, user.id,
                )
                raise credentials_exception

            # Throttled last_active update: at most one DB write per
            # configured window per session, regardless of request volume.
            from domains.auth.session_repository import SessionRepository
            if redis is not None:
                try:
                    throttle = _session_throttle_key(sid)
                    if not await redis.get(throttle):
                        await SessionRepository(db).update_last_active(session.id)
                        await db.commit()
                        await redis.setex(
                            throttle,
                            settings.AUTH_SESSION_LAST_ACTIVE_THROTTLE_SECONDS,
                            "1",
                        )
                except Exception as exc:
                    logger.warning("Session last_active throttle write failed (%s)", exc)
            else:
                await SessionRepository(db).update_last_active(session.id)
                await db.commit()

    await db.refresh(user, attribute_names=["user_roles"])

    if token_type != _TOKEN_TYPE_ONBOARDING and not user.onboarding_completed:
        logger.warning("Auth rejected — onboarding incomplete: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account setup incomplete. Please complete onboarding.",
        )

    return user


async def get_current_user_for_onboarding(
    token: Annotated[str, Depends(_oauth2_scheme)],
    db:    Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Variant of get_current_user that accepts onboarding-scoped tokens."""
    return await get_current_user(token=token, db=db, allow_onboarding_scope=True)


# ------------------------------------------------------------------ #
#  WebSocket auth helper                                              #
# ------------------------------------------------------------------ #

async def ws_get_current_user(
    token: str,
    db: AsyncSession,
) -> User | None:
    """
    WebSocket-safe authentication. JWT passed as query parameter (?token=<jwt>).
    Returns None instead of raising so the WS endpoint can close cleanly.
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

    return user


# ------------------------------------------------------------------ #
#  RBAC dependency factory                                            #
# ------------------------------------------------------------------ #

# Plan 23 Fase 3 — Redis-cached permission lookup. Admins bypass entirely
# (no DB hop, no cache hit). Cache key namespaces per user; invalidated
# when an admin grants/revokes a role/permission or when the user does a
# global logout (token_version bump).
_PERM_CACHE_TTL_SECONDS = 600  # 10 min — short enough that a stale cache
                               # entry after a role change self-heals fast.


def _permission_cache_key(user_id: uuid.UUID) -> str:
    return f"permissions:{user_id}"


async def _has_permission_cached(
    user: User, permission_name: str, redis, db: AsyncSession | None = None,
) -> bool:
    """Return True iff `user` carries `permission_name` (e.g.
    "write:appointments"). Reads from Redis on the hot path; falls back
    to a SQL lookup on cache miss + populates.

    `*:*` is treated as a wildcard so a super-admin role with that grant
    matches every check without listing them individually.
    """
    import json as _json
    key = _permission_cache_key(user.id)

    if redis is not None:
        try:
            cached = await redis.get(key)
            if cached:
                perms = set(_json.loads(cached))
                return permission_name in perms or "*:*" in perms
        except Exception as exc:
            logger.warning("Permission cache read failed (%s) — falling back to DB", exc)

    # DB fallback. Prefer a direct SQL JOIN so we don't depend on the
    # ORM having eager-loaded user.user_roles → role → permissions.
    from domains.auth.models import Permission, Role, RolePermission, UserRoleAssociation
    from sqlalchemy import select

    perms: set[str]
    if db is not None:
        stmt = (
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRoleAssociation, UserRoleAssociation.role_id == Role.id)
            .where(UserRoleAssociation.user_id == user.id)
        )
        rows = (await db.execute(stmt)).scalars().all()
        perms = set(rows)
    else:
        # Last-resort path — works only when caller has already eager-loaded
        # the ORM graph (true in get_current_user but not in arbitrary
        # callers). Kept so we degrade gracefully without a db handle.
        try:
            perms = user.get_all_permissions()
        except Exception as exc:
            logger.warning("Permission DB lookup unavailable (%s)", exc)
            return False

    if redis is not None:
        try:
            await redis.setex(key, _PERM_CACHE_TTL_SECONDS, _json.dumps(list(perms)))
        except Exception as exc:
            logger.warning("Permission cache write failed (%s)", exc)
    return permission_name in perms or "*:*" in perms


async def invalidate_permission_cache(user_id: uuid.UUID, redis) -> None:
    """Drop the cached permission set for a user. Call after any role /
    permission grant or revoke."""
    if redis is None:
        return
    try:
        await redis.delete(_permission_cache_key(user_id))
    except Exception as exc:
        logger.warning("Permission cache invalidate failed (%s)", exc)


def require_permission(action: str, resource: str):
    """Dependency factory that 403s unless the caller carries the
    `{action}:{resource}` permission. Admins bypass the check.

    Usage:
        @router.get(
            "/api/v1/audit-logs",
            dependencies=[Depends(require_permission("read", "audit_logs"))],
        )

    Wraps the user response so existing handlers that take
    `Depends(require_permission(...))` and consume the user keep working
    unchanged.
    """
    permission_name = f"{action}:{resource}"

    async def _dep(
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)],
        redis = Depends(get_redis),
    ) -> User:
        if current_user.is_admin():
            return current_user
        if not await _has_permission_cached(current_user, permission_name, redis, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission_name}",
            )
        return current_user

    return _dep


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
