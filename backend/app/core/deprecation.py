"""
app/core/deprecation.py — Helpers to mark legacy endpoints as deprecated.

When endpoints migrate (e.g. `GET /auth/me` → `GET /api/v1/users/me`), the old
endpoint stays online for two sprints emitting the following response headers:

    Deprecation: true
    Sunset: 2026-08-01
    Link: </api/v1/users/me>; rel="successor-version"

This follows RFC 8594 (Sunset) and the IETF Deprecation HTTP Header draft.
Clients can detect deprecated endpoints in logs/observability and migrate
before the Sunset date.

Usage in a router:

    from app.core.deprecation import deprecated

    @router.get("/auth/me", dependencies=[Depends(deprecated(
        sunset="2026-08-01",
        successor="/api/v1/users/me",
    ))])
    async def get_me(...):
        ...
"""
from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response

logger = logging.getLogger(__name__)


def deprecated(
    *,
    sunset: str,
    successor: str | None = None,
    reason: str | None = None,
) -> Callable:
    """
    Returns a FastAPI dependency that attaches deprecation headers to the response.

    Args:
        sunset: ISO date when the endpoint will return 410 Gone (e.g. "2026-08-01").
        successor: Replacement URL path (e.g. "/api/v1/users/me"). Optional.
        reason: Short human-readable explanation. Optional. Logged for observability.
    """

    async def _dep(request: Request, response: Response) -> None:
        response.headers["Deprecation"] = "true"
        response.headers["Sunset"] = sunset
        if successor:
            response.headers["Link"] = f'<{successor}>; rel="successor-version"'
        # Emit a structured log event so dashboards can count deprecated calls
        logger.info(
            "deprecated_endpoint_call",
            extra={
                "path": request.url.path,
                "method": request.method,
                "sunset": sunset,
                "successor": successor,
                "reason": reason,
            },
        )

    return _dep
