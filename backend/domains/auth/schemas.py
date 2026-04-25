from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from shared.schemas import _BaseSchema, _BaseRequestSchema, _validate_password_strength


# ── Core auth ────────────────────────────────────────────────────── #

class Token(_BaseSchema):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("password", mode="after")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower().strip()


class LoginResponse(_BaseSchema):
    access_token: str | None = None
    refresh_token: str | None = None
    onboarding_token: str | None = None
    roles: list[str] = Field(default_factory=list)
    onboarding_completed: bool = False
    next_step: str


class LogoutRequest(BaseModel):
    refresh_token: str


class CheckEmailRequest(BaseModel):
    email: EmailStr


class CheckEmailResponse(_BaseSchema):
    email: str
    exists: bool
    auth_method: str
    suggested_action: str


class IdentifierRequest(BaseModel):
    identifier: str = Field(..., description="Email address or phone number.")
    identifier_type: str | None = Field(default=None)


class IdentifierResponse(_BaseSchema):
    identifier: str
    identifier_type: str
    exists: bool
    auth_methods: list[str]
    is_new_user: bool
    suggested_action: str


class VerifyRequest(BaseModel):
    identifier: str
    identifier_type: str
    provider: str | None = None
    password: str | None = None
    access_token: str | None = None
    otp_code: str | None = None


class VerifyResponse(_BaseSchema):
    access_token: str | None = None
    refresh_token: str | None = None
    is_new_user: bool
    temp_token: str | None = None
    needs_profile_completion: bool = False
    next_step: str
    assigned_role: str | None = None


class CompleteProfileRequest(BaseModel):
    full_name: str
    phone_number: str | None = None
    role: str = Field(default="client")


class TokenData(_BaseSchema):
    user_id: uuid.UUID
    role: str


# ── Social login ──────────────────────────────────────────────────── #

class GoogleLoginRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: str


class AppleLoginRequest(BaseModel):
    identity_token: str
    full_name: str | None = Field(default=None, max_length=120)


class SocialAuthResponse(BaseModel):
    is_new_user: bool
    onboarding_required: bool = False
    onboarding_token: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    active_role: str | None = None


# ── Password reset ────────────────────────────────────────────────── #

class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password", mode="after")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class PasswordResetConfirmResponse(BaseModel):
    message: str


class PasswordResetResponse(BaseModel):
    message: str


# ── WebAuthn / FIDO2 ─────────────────────────────────────────────── #

class WebAuthnRegisterBeginResponse(_BaseSchema):
    challenge_token: str
    options: dict


class WebAuthnRegisterCompleteRequest(_BaseRequestSchema):
    challenge_token: str
    credential: dict
    device_name: str = Field(default="My Device", max_length=120)


class WebAuthnRegisterCompleteResponse(_BaseSchema):
    credential_id: str
    device_name: str


class WebAuthnAuthBeginRequest(_BaseRequestSchema):
    email: str


class WebAuthnAuthBeginResponse(_BaseSchema):
    challenge_token: str
    options: dict


class WebAuthnAuthCompleteRequest(_BaseRequestSchema):
    challenge_token: str
    credential: dict


class WebAuthnCredentialRead(_BaseSchema):
    id: uuid.UUID
    credential_id: str
    device_name: str | None
    created_at: datetime
    last_used_at: datetime | None


class WebAuthnCredentialsListResponse(_BaseSchema):
    credentials: list[WebAuthnCredentialRead]
    total: int


class WebAuthnCredentialRenameRequest(_BaseRequestSchema):
    device_name: str = Field(..., min_length=1, max_length=120)


class WebAuthnCredentialDeleteResponse(_BaseSchema):
    deleted_id: uuid.UUID
    message: str


# ── Session management ────────────────────────────────────────────── #

class SessionRead(_BaseSchema):
    family_id: uuid.UUID
    created_at: datetime
    last_used_at: datetime | None
    revoked: bool
    expires_at: datetime


class SessionsListResponse(_BaseSchema):
    sessions: list[SessionRead]
    total: int


class SessionRevokeResponse(_BaseSchema):
    revoked_family_id: uuid.UUID
    message: str
