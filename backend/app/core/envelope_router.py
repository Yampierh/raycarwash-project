"""
app/core/envelope_router.py — Custom APIRouter that enforces `response_model`
derives from `Envelope` or `PaginatedEnvelope` (per ADR-007).

Use this for any new router under /api/v1/users/me/* and /api/v1/auth/* security
endpoints. Legacy routers may keep using the stock `APIRouter`.

Enforcement happens at route-registration time (when @router.get/post/... is
called), so misconfigured routers raise ImportError at module load — far before
the first request hits production.

Allowed shapes per route:
  - response_model derives from Envelope, PaginatedEnvelope, or ErrorEnvelope
  - response_model is None AND status_code is 204 (No Content)
  - endpoint function is decorated with @envelope_exempt
    (use sparingly — e.g. for raw file streams or webhook receivers)

Usage:
    from app.core.envelope_router import EnvelopeRouter, envelope_exempt
    router = EnvelopeRouter(prefix="/api/v1/users/me", tags=["users"])

    @router.get("/profile", response_model=Envelope[ProfileBlock])
    async def get_profile(...): ...

    @router.get("/avatar/raw")
    @envelope_exempt
    async def raw_avatar(): return FileResponse(...)
"""
from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter
from fastapi.datastructures import DefaultPlaceholder

from shared.schemas import Envelope, ErrorEnvelope, PaginatedEnvelope


class EnvelopeContractError(TypeError):
    """Raised when a route is registered without a compliant `response_model`."""


_EXEMPT_ATTR = "_envelope_exempt"


def envelope_exempt(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Mark an endpoint as exempt from envelope enforcement. Use sparingly."""
    setattr(fn, _EXEMPT_ATTR, True)
    return fn


class EnvelopeRouter(APIRouter):
    """
    Drop-in replacement for `fastapi.APIRouter` that enforces the envelope contract.

    Mark exempt endpoints with `@envelope_exempt` (see module docstring).
    """

    def add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        *,
        response_model: Any = None,
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        if not getattr(endpoint, _EXEMPT_ATTR, False):
            self._enforce_envelope(
                path=path,
                response_model=response_model,
                status_code=status_code,
                endpoint=endpoint,
            )
        super().add_api_route(
            path,
            endpoint,
            response_model=response_model,
            status_code=status_code,
            **kwargs,
        )

    @staticmethod
    def _enforce_envelope(
        *,
        path: str,
        response_model: Any,
        status_code: int | None,
        endpoint: Callable[..., Any],
    ) -> None:
        # FastAPI passes DefaultPlaceholder when the user did not specify a model.
        no_model = response_model is None or isinstance(response_model, DefaultPlaceholder)

        # 204 No Content can have no body
        if status_code == 204 and no_model:
            return

        if no_model:
            raise EnvelopeContractError(
                f"EnvelopeRouter: route {endpoint.__name__} @ '{path}' has no response_model. "
                "Declare `response_model=Envelope[T]` or set `envelope_exempt=True` "
                "(see app/core/envelope_router.py)."
            )

        if not _is_envelope(response_model):
            raise EnvelopeContractError(
                f"EnvelopeRouter: route {endpoint.__name__} @ '{path}' has "
                f"response_model={response_model!r}, which does not derive from Envelope. "
                "Use `Envelope[T]`, `PaginatedEnvelope[T]`, or `ErrorEnvelope`."
            )


def _is_envelope(model: Any) -> bool:
    """True if `model` is Envelope[...], PaginatedEnvelope[...], or ErrorEnvelope."""
    origin = getattr(model, "__pydantic_generic_metadata__", {}).get("origin")
    candidates = (Envelope, PaginatedEnvelope, ErrorEnvelope)
    if origin in candidates:
        return True
    try:
        if isinstance(model, type) and issubclass(model, candidates):
            return True
    except TypeError:
        pass
    return False
