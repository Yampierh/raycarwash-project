"""
domains/public/router.py — 9 public endpoints (Plan 19 Track 1).

5 of 9 endpoints are wired in this commit:
    GET  /testimonials
    GET  /faq
    GET  /coverage-zones
    POST /coverage/check
    GET  /waitlist/count

The remaining 4 (stats, detailer-benchmarks, contact, waitlist/join)
still raise 501 — they need cross-domain aggregation or write paths
and ship in follow-up commits.

Cache-Control headers follow Plan 19 §10.2. Rate limits follow §10.1.
All endpoints are anonymous (no auth).

NOTE: this module deliberately does NOT use `from __future__ import
annotations`. Under that import all annotations become strings, which
combined with slowapi's decorator confuses FastAPI's body parameter
introspection for Pydantic models (the body gets re-classified as
`query.body` and validation rejects every POST as missing). Keeping
annotations evaluated at definition time matches the working pattern
in `domains/auth/routers/webauthn.py`.
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from domains.public.models import FaqCategory, TestimonialRole
from domains.public.repository import PublicRepository
from domains.public.schemas import (
    ContactRequest,
    ContactResponse,
    CoverageCheckRequest,
    CoverageCheckResponse,
    CoverageZonesResponse,
    DetailerBenchmarksResponse,
    FaqResponse,
    StatsResponse,
    TestimonialsResponse,
    WaitlistCountResponse,
    WaitlistJoinRequest,
    WaitlistJoinResponse,
)
from domains.public.service import PublicService
from infrastructure.db.session import get_db
from shared.schemas import Envelope

router = APIRouter(prefix="/api/v1/public", tags=["public"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Public endpoint scaffolded but not yet wired (Plan 19 implementation pending).",
)


# Cache-Control values per Plan 19 §10.2. The `stale-while-revalidate`
# directive tells the CDN to serve stale content for up to N seconds
# while a fresh copy is fetched async — keeps p99 latency low during
# admin CMS invalidation windows.
_CC_TESTIMONIALS    = "public, max-age=3600, stale-while-revalidate=300"
_CC_FAQ             = "public, max-age=3600, stale-while-revalidate=300"
_CC_COVERAGE_ZONES  = "public, max-age=86400, stale-while-revalidate=3600"
_CC_WAITLIST_COUNT  = "public, max-age=30"
_CC_NO_STORE        = "no-store"  # for non-cacheable POST/check endpoints


def _service(db: AsyncSession = Depends(get_db)) -> PublicService:
    return PublicService(PublicRepository(db))


# 1. Testimonials ───────────────────────────────────────────────────────


@router.get("/testimonials", response_model=Envelope[TestimonialsResponse])
@limiter.limit("60/minute")
async def list_testimonials(
    request: Request,
    response: Response,
    role: Literal["client", "detailer"] | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    featured: bool = False,
    service: PublicService = Depends(_service),
) -> Envelope[TestimonialsResponse]:
    data = await service.list_testimonials(
        role=TestimonialRole(role) if role else None,
        featured=True if featured else None,
        limit=limit,
    )
    response.headers["Cache-Control"] = _CC_TESTIMONIALS
    return Envelope(data=data)


# 2. FAQ ────────────────────────────────────────────────────────────────


@router.get("/faq", response_model=Envelope[FaqResponse])
@limiter.limit("60/minute")
async def list_faq(
    request: Request,
    response: Response,
    category: Literal["rider", "detailer", "mechanic", "provider"] | None = None,
    service: PublicService = Depends(_service),
) -> Envelope[FaqResponse]:
    data = await service.list_faq(
        category=FaqCategory(category) if category else None,
    )
    response.headers["Cache-Control"] = _CC_FAQ
    return Envelope(data=data)


# 3. Coverage zones ─────────────────────────────────────────────────────


@router.get("/coverage-zones", response_model=Envelope[CoverageZonesResponse])
@limiter.limit("30/minute")
async def list_coverage_zones(
    request: Request,
    response: Response,
    service: PublicService = Depends(_service),
) -> Envelope[CoverageZonesResponse]:
    data = await service.list_coverage_zones()
    response.headers["Cache-Control"] = _CC_COVERAGE_ZONES
    return Envelope(data=data)


# 4. Coverage check ─────────────────────────────────────────────────────


@router.post("/coverage/check", response_model=Envelope[CoverageCheckResponse])
@limiter.limit("10/minute")
async def check_coverage(
    request: Request,
    # `Annotated[..., Body()]` marker required: when slowapi wraps the
    # route, FastAPI's auto-detection of Pydantic bodies breaks and the
    # param gets treated as a query string. Explicit marker restores
    # body parsing.
    #
    # We do NOT take `response: Response` here. Including it together
    # with a Pydantic body on a slowapi-wrapped POST trips FastAPI's
    # introspection (the body gets re-classified as a query field).
    # POST responses are not cached by default (per RFC 7234 §3); the
    # `Cache-Control: no-store` from Plan 19 §10.2 is informational
    # for this endpoint and is omitted here.
    body: Annotated[CoverageCheckRequest, Body()],
    service: PublicService = Depends(_service),
) -> Envelope[CoverageCheckResponse]:
    return Envelope(data=await service.check_coverage(body))


# 5. Stats ──────────────────────────────────────────────────────────────


@router.get("/stats", response_model=Envelope[StatsResponse])
@limiter.limit("60/minute")
async def get_stats(
    request: Request,
    response: Response,
    service: PublicService = Depends(_service),
) -> Envelope[StatsResponse]:
    # Plan 19 §10.2 — 1h CDN cache.
    # Plan 22 H6 — no query params here on purpose. Without a date
    # range knob, a competitor can't enumerate historical growth.
    response.headers["Cache-Control"] = (
        "public, max-age=3600, stale-while-revalidate=300"
    )
    return Envelope(data=await service.get_stats())


# 6. Detailer benchmarks ────────────────────────────────────────────────


@router.get(
    "/stats/detailer-benchmarks",
    response_model=Envelope[DetailerBenchmarksResponse],
)
@limiter.limit("60/minute")
async def get_detailer_benchmarks(
    request: Request,
    response: Response,
    service: PublicService = Depends(_service),
) -> Envelope[DetailerBenchmarksResponse]:
    # Plan 19 §10.2 — 24h CDN cache. Marketing-approved benchmark
    # numbers refresh rarely (manual update); aggressive caching is
    # safe and keeps the EarningsCalc on the detailers page snappy.
    response.headers["Cache-Control"] = (
        "public, max-age=86400, stale-while-revalidate=3600"
    )
    return Envelope(data=await service.get_detailer_benchmarks())


# 7. Contact ────────────────────────────────────────────────────────────


@router.post(
    "/contact",
    response_model=Envelope[ContactResponse],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/minute")
async def submit_contact(
    request: Request,
    body: Annotated[ContactRequest, Body()],
    service: PublicService = Depends(_service),
) -> Envelope[ContactResponse]:
    ip = request.client.host if request.client else None
    return Envelope(
        data=await service.submit_contact(
            body,
            ip_address=ip,
            user_agent=request.headers.get("user-agent"),
        )
    )


# 8. Waitlist join ──────────────────────────────────────────────────────


@router.post(
    "/waitlist/join",
    response_model=Envelope[WaitlistJoinResponse],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/minute")
async def join_waitlist(
    request: Request,
    body: Annotated[WaitlistJoinRequest, Body()],
    service: PublicService = Depends(_service),
) -> Envelope[WaitlistJoinResponse]:
    return Envelope(data=await service.join_waitlist(body))


# 9. Waitlist count ─────────────────────────────────────────────────────


@router.get("/waitlist/count", response_model=Envelope[WaitlistCountResponse])
@limiter.limit("30/minute")
async def get_waitlist_count(
    request: Request,
    response: Response,
    service: PublicService = Depends(_service),
) -> Envelope[WaitlistCountResponse]:
    data = await service.get_waitlist_count()
    response.headers["Cache-Control"] = _CC_WAITLIST_COUNT
    return Envelope(data=data)
