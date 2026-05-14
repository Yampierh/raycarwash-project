"""
shared/schemas.py — Cross-domain Pydantic base classes and generic response types.

Import from here, never from app.schemas.schemas, for new domain code.

Profile system (Phase 0) introduces `Envelope[T]`, `PaginatedEnvelope[T]`, `ErrorEnvelope`,
and `Meta` for uniform API responses under /api/v1/*. Legacy classes (`PaginatedResponse`,
`ErrorDetail`) are kept for backwards compatibility with pre-Phase 0 endpoints.
"""
from __future__ import annotations

import re
from typing import Any, Generic, TypeVar

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
    """Legacy error shape — use ErrorEnvelope for new endpoints."""
    code: str = Field(..., examples=["VALIDATION_ERROR", "NOT_FOUND"])
    message: str
    details: list[dict] | None = Field(default=None)


class PaginatedResponse(_BaseSchema):
    """Legacy paginated shape (page-based) — use PaginatedEnvelope (cursor-based) for new endpoints."""
    items: list[Any]
    total: int
    page: int
    page_size: int
    pages: int

    @classmethod
    def build(cls, items: list[Any], total: int, page: int, page_size: int) -> PaginatedResponse:
        pages = max(1, -(-total // page_size))
        return cls(items=items, total=total, page=page, page_size=page_size, pages=pages)


# ─── Envelope generics (Phase 0) ──────────────────────────────────────────────

T = TypeVar("T")


class FieldError(_BaseSchema):
    field: str
    reason: str


class ErrorPayload(_BaseSchema):
    """Standardized error body. `code` is a machine-readable identifier."""
    code: str = Field(..., examples=[
        "bad_request", "authentication_required", "step_up_required",
        "permission_denied", "resource_not_found", "conflict",
        "validation_failed", "rate_limit_exceeded", "internal_error",
    ])
    message: str
    details: list[FieldError] | None = None
    request_id: str | None = None


class Meta(_BaseSchema):
    """Optional metadata block. Endpoints populate the fields they need."""
    # Cursor pagination
    cursor: str | None = None
    prev_cursor: str | None = None
    has_more: bool | None = None
    limit: int | None = None
    # Profile Hub
    includes: list[str] | None = None
    # Step-up
    requires_step_up: list[str] | None = None
    skipped_due_to_step_up: list[str] | None = None


class Envelope(_BaseSchema, Generic[T]):
    """Uniform success envelope. `data` carries the resource (object, list, or composite)."""
    data: T
    meta: Meta | None = None
    links: dict[str, str] | None = None


class PaginatedEnvelope(_BaseSchema, Generic[T]):
    """List endpoints with cursor pagination. `meta` is always populated."""
    data: list[T]
    meta: Meta
    links: dict[str, str] | None = None


class ErrorEnvelope(_BaseSchema):
    """Uniform error envelope. Returned for any non-2xx response from /api/v1/*."""
    error: ErrorPayload
    meta: Meta | None = None  # carries step-up info on 401 step_up_required


# Convenience type aliases — use these when authoring endpoints
__all__ = [
    "_BaseSchema",
    "_BaseRequestSchema",
    "PositiveCents",
    "HealthResponse",
    "ErrorDetail",
    "PaginatedResponse",
    "Envelope",
    "PaginatedEnvelope",
    "ErrorEnvelope",
    "ErrorPayload",
    "FieldError",
    "Meta",
]
