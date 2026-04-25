from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from shared.schemas import _BaseSchema, _BaseRequestSchema


class UserCreate(_BaseRequestSchema):
    email: EmailStr = Field(..., examples=["jane.doe@example.com"])
    full_name: str = Field(..., min_length=2, max_length=120)
    phone_number: str | None = Field(default=None, pattern=r"^\+?[1-9]\d{1,14}$")
    password: str = Field(..., min_length=8, max_length=128)
    role_names: list[str] | None = Field(default=None)

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("role_names", mode="before")
    @classmethod
    def restrict_admin_registration(cls, v: list[str] | None) -> list[str] | None:
        if v and "admin" in v:
            raise ValueError("No es posible registrarse como ADMIN.")
        return v


class UserRead(_BaseSchema):
    id: uuid.UUID
    email: str
    full_name: str | None = Field(default=None)
    phone_number: str | None = Field(default=None)
    roles: list[str]
    onboarding_completed: bool
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(_BaseRequestSchema):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone_number: str | None = Field(default=None, pattern=r"^\+?[1-9]\d{1,14}$")
