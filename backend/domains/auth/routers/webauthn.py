import base64
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn.helpers import bytes_to_base64url

from app.core.config import get_settings
from app.core.limiter import limiter
from infrastructure.db.session import get_db
from domains.auth.schemas import (
    Token,
    WebAuthnAuthBeginRequest,
    WebAuthnAuthBeginResponse,
    WebAuthnAuthCompleteRequest,
    WebAuthnCredentialDeleteResponse,
    WebAuthnCredentialRead,
    WebAuthnCredentialRenameRequest,
    WebAuthnCredentialsListResponse,
    WebAuthnRegisterBeginResponse,
    WebAuthnRegisterCompleteRequest,
    WebAuthnRegisterCompleteResponse,
)
from domains.auth.service import (
    AuthService,
    TOKEN_TYPE_WEBAUTHN_REG,
    TOKEN_TYPE_WEBAUTHN_AUTH,
    get_current_user,
)
from domains.auth.webauthn_repository import WebAuthnRepository
from domains.auth.webauthn_service import WebAuthnService
from domains.users.models import User
from domains.users.repository import UserRepository

logger   = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


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
    """Step 1 of passkey registration. Returns a challenge_token (Redis session ID) and options."""
    from infrastructure.redis.client import get_redis

    challenge = os.urandom(32)
    existing = await WebAuthnRepository(db).get_credentials_by_user(current_user.id)

    options = WebAuthnService.generate_registration_options(
        user=current_user,
        existing_credentials=existing,
        challenge=challenge,
    )

    redis = await get_redis(request)
    ttl = settings.WEBAUTHN_CHALLENGE_EXPIRE_MINUTES * 60
    challenge_token = await WebAuthnService.store_challenge(
        redis=redis,
        user_id=current_user.id,
        challenge_bytes=challenge,
        ctype=TOKEN_TYPE_WEBAUTHN_REG,
        ttl_seconds=ttl,
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
    """Step 2 of passkey registration. Verifies attestation and stores the credential."""
    from webauthn.helpers.exceptions import InvalidRegistrationResponse
    from domains.auth.models import WebAuthnCredential
    from infrastructure.redis.client import get_redis

    redis = await get_redis(request)
    result = await WebAuthnService.consume_challenge(
        redis=redis,
        session_id=body.challenge_token,
        expected_type=TOKEN_TYPE_WEBAUTHN_REG,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired WebAuthn challenge. Please restart registration.",
        )
    user_id, challenge = result
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Challenge user mismatch.")

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
    """Step 1 of passkey authentication. Public endpoint — no Bearer token required."""
    from infrastructure.redis.client import get_redis

    user = await UserRepository(db).get_by_email(body.email.lower().strip())
    if not user or not user.is_active or user.is_deleted:
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

    options = WebAuthnService.generate_authentication_options(
        credentials=credentials,
        challenge=challenge,
    )

    redis = await get_redis(request)
    ttl = settings.WEBAUTHN_CHALLENGE_EXPIRE_MINUTES * 60
    challenge_token = await WebAuthnService.store_challenge(
        redis=redis,
        user_id=user.id,
        challenge_bytes=challenge,
        ctype=TOKEN_TYPE_WEBAUTHN_AUTH,
        ttl_seconds=ttl,
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
    """Step 2 of passkey authentication. Returns access + refresh token pair."""
    from webauthn.helpers import base64url_to_bytes
    from webauthn.helpers.exceptions import InvalidAuthenticationResponse
    from datetime import datetime, timezone
    from infrastructure.redis.client import get_redis

    redis = await get_redis(request)
    result = await WebAuthnService.consume_challenge(
        redis=redis,
        session_id=body.challenge_token,
        expected_type=TOKEN_TYPE_WEBAUTHN_AUTH,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired WebAuthn challenge. Please restart authentication.",
        )
    user_id, challenge = result

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

    await repo.update_sign_count(
        credential_id=raw_credential_id,
        sign_count=verified.new_sign_count,
        last_used_at=datetime.now(timezone.utc),
    )

    user = await UserRepository(db).get_by_id(user_id)
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is inactive.")

    _role         = user.primary_role or "client"
    access_token  = AuthService.create_access_token(user.id, _role, token_version=getattr(user, "token_version", 1))
    refresh_token = await AuthService.create_refresh_token(user.id, _role, db)

    # Hotfix H3 — passkey verification is a real auth event (FIDO2 sign).
    await AuthService.record_step_up_success(request, user, db, auth_method="webauthn")

    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get(
    "/webauthn/credentials",
    response_model=WebAuthnCredentialsListResponse,
    summary="List registered passkeys for the current user.",
)
async def list_webauthn_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WebAuthnCredentialsListResponse:
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
    repo = WebAuthnRepository(db)
    updated = await repo.rename_credential(credential_id, current_user.id, body.device_name)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passkey not found.")
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
    """Refuses to delete the last passkey when the user has no other auth method."""
    repo = WebAuthnRepository(db)

    cred = await repo.get_by_pk_and_user(credential_id, current_user.id)
    if cred is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passkey not found.")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Passkey not found.")
    await db.commit()
    return WebAuthnCredentialDeleteResponse(
        deleted_id=credential_id,
        message="Passkey removed successfully.",
    )
