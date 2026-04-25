"""
shared/schemas.py — Cross-domain Pydantic base classes and generic response types.

Import from here, never from app.schemas.schemas, for new domain code.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _BaseSchema(BaseModel):
    """Base for all response schemas. Builds from ORM objects via from_attributes=True."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class _BaseRequestSchema(BaseModel):
    """Base for all request schemas. No from_attributes — input always comes from JSON."""
    model_config = ConfigDict(str_strip_whitespace=True)


PositiveCents = int


def _validate_password_strength(v: str) -> str:
    errors = []
    if not re.search(r"[A-Z]", v):
        errors.append("one uppercase letter")
    if not re.search(r"[a-z]", v):
        errors.append("one lowercase letter")
    if not re.search(r"\d", v):
        errors.append("one digit")
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>?/\\|`~]", v):
        errors.append("one special character (!@#$%^&* etc.)")
    if errors:
        raise ValueError(f"Password must contain at least: {', '.join(errors)}.")
    return v


class HealthResponse(_BaseSchema):
    status: str = "ok"
    service: str
    version: str
    db_reachable: bool


class ErrorDetail(_BaseSchema):
    code: str = Field(..., examples=["VALIDATION_ERROR", "NOT_FOUND"])
    message: str
    details: list[dict] | None = Field(default=None)


class PaginatedResponse(_BaseSchema):
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: list[Any], total: int, page: int, page_size: int) -> PaginatedResponse:
        pages = max(1, -(-total // page_size))
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)
