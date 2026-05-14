"""
app/exception_handlers.py — Maps ValidationError, HTTPException, BusinessError
into the standardized `ErrorEnvelope` shape.

Registered in main.py via `register_exception_handlers(app)`.

Conventions (per plan §3.3):
  - 400 bad_request                 — malformed JSON / unparseable params
  - 401 authentication_required     — missing or invalid token
  - 401 step_up_required            — step-up needed; includes WWW-Authenticate header
  - 403 permission_denied           — token valid but unauthorized
  - 404 resource_not_found          — visible-to-caller resource missing
  - 409 conflict                    — state mismatch (e.g. delete vehicle with active appt)
  - 422 validation_failed           — Pydantic validation
  - 423 account_locked              — locked due to failures or pending deletion
  - 429 rate_limit_exceeded         — slowapi
  - 500 internal_error              — unhandled bug
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from shared.schemas import ErrorEnvelope, ErrorPayload, FieldError, Meta

logger = logging.getLogger(__name__)


class BusinessError(Exception):
    """
    Raise from service layer when domain rules reject an operation.
    Routers don't need to catch this — the handler maps it to HTTP.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = status.HTTP_409_CONFLICT,
        details: list[dict] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def register_exception_handlers(app: FastAPI) -> None:
    """Install all handlers on the FastAPI app instance."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        # HTTPException.detail may be a dict (from step_up.py) or a string
        if isinstance(exc.detail, dict):
            code = exc.detail.get("code", _default_code(exc.status_code))
            message = exc.detail.get("message", _default_message(exc.status_code))
            details_raw = exc.detail.get("details")
            requires_step_up = exc.detail.get("requires_step_up")
        else:
            code = _default_code(exc.status_code)
            message = str(exc.detail) if exc.detail else _default_message(exc.status_code)
            details_raw = None
            requires_step_up = None

        meta = None
        if requires_step_up:
            meta = Meta(requires_step_up=requires_step_up)

        return _envelope(
            status_code=exc.status_code,
            code=code,
            message=message,
            request_id=_request_id(request),
            details=_normalize_details(details_raw),
            meta=meta,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _envelope(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_failed",
            message="The request contains invalid fields.",
            request_id=_request_id(request),
            details=_normalize_details(exc.errors()),
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return _envelope(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_failed",
            message="Schema validation failed.",
            request_id=_request_id(request),
            details=_normalize_details(exc.errors()),
        )

    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
        return _envelope(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            request_id=_request_id(request),
            details=_normalize_details(exc.details),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception during request %s %s", request.method, request.url.path)
        return _envelope(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_error",
            message="An unexpected error occurred. Reference the request_id when contacting support.",
            request_id=_request_id(request),
        )


# ─── helpers ──────────────────────────────────────────────────────────────────


def _envelope(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str | None,
    details: list[FieldError] | None = None,
    meta: Meta | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    envelope = ErrorEnvelope(
        error=ErrorPayload(
            code=code,
            message=message,
            details=details,
            request_id=request_id,
        ),
        meta=meta,
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(envelope, exclude_none=True),
        headers=headers,
    )


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _normalize_details(raw: Any) -> list[FieldError] | None:
    if not raw:
        return None
    if isinstance(raw, list):
        normalized: list[FieldError] = []
        for item in raw:
            if isinstance(item, FieldError):
                normalized.append(item)
            elif isinstance(item, dict):
                # Pydantic v2 error format: {"loc": [...], "msg": "...", "type": "..."}
                field = ".".join(str(p) for p in item.get("loc", [])) or item.get("field", "")
                reason = item.get("msg") or item.get("reason") or item.get("type", "invalid")
                normalized.append(FieldError(field=field, reason=str(reason)))
        return normalized or None
    return None


_DEFAULT_CODES = {
    400: "bad_request",
    401: "authentication_required",
    403: "permission_denied",
    404: "resource_not_found",
    409: "conflict",
    410: "gone",
    422: "validation_failed",
    423: "account_locked",
    429: "rate_limit_exceeded",
    500: "internal_error",
    503: "service_unavailable",
}

_DEFAULT_MESSAGES = {
    400: "Malformed request.",
    401: "Authentication required.",
    403: "You do not have permission to perform this action.",
    404: "Resource not found.",
    409: "Operation conflicts with current state.",
    410: "This resource is no longer available.",
    422: "Request validation failed.",
    423: "Account is locked.",
    429: "Too many requests. Please retry later.",
    500: "An unexpected error occurred.",
    503: "Service temporarily unavailable.",
}


def _default_code(status_code: int) -> str:
    return _DEFAULT_CODES.get(status_code, "error")


def _default_message(status_code: int) -> str:
    return _DEFAULT_MESSAGES.get(status_code, "Request failed.")
