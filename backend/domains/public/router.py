"""
domains/public/router.py — 9 public endpoints (Plan 19 Track 1).

Stub for Paso 3. Routes are declared with signatures and limiter
decorators (so rate-limit config is ready) but bodies raise 501 until
the service layer is implemented. NOT mounted in `api/router.py` yet
— mount happens after Paso 4 (migrations + seed) lands.

Rate limits per Plan 19 §10.1. All endpoints are anonymous (no auth).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.limiter import limiter
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
from shared.schemas import Envelope

router = APIRouter(prefix="/public", tags=["public"])

_NOT_IMPLEMENTED = HTTPException(
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    detail="Public endpoint scaffolded but not yet wired (Plan 19 implementation pending).",
)


# 1. Testimonials ───────────────────────────────────────────────────────


@router.get("/testimonials", response_model=Envelope[TestimonialsResponse])
@limiter.limit("60/minute")
async def list_testimonials(
    request: Request,
    role: Literal["client", "detailer"] | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    featured: bool = False,
) -> Envelope[TestimonialsResponse]:
    raise _NOT_IMPLEMENTED


# 2. FAQ ────────────────────────────────────────────────────────────────


@router.get("/faq", response_model=Envelope[FaqResponse])
@limiter.limit("60/minute")
async def list_faq(
    request: Request,
    category: Literal["rider", "detailer", "mechanic", "provider"] | None = None,
) -> Envelope[FaqResponse]:
    raise _NOT_IMPLEMENTED


# 3. Coverage zones ─────────────────────────────────────────────────────


@router.get("/coverage-zones", response_model=Envelope[CoverageZonesResponse])
@limiter.limit("30/minute")
async def list_coverage_zones(request: Request) -> Envelope[CoverageZonesResponse]:
    raise _NOT_IMPLEMENTED


# 4. Coverage check ─────────────────────────────────────────────────────


@router.post("/coverage/check", response_model=Envelope[CoverageCheckResponse])
@limiter.limit("10/minute")
async def check_coverage(
    request: Request,
    body: CoverageCheckRequest,
) -> Envelope[CoverageCheckResponse]:
    raise _NOT_IMPLEMENTED


# 5. Stats ──────────────────────────────────────────────────────────────


@router.get("/stats", response_model=Envelope[StatsResponse])
@limiter.limit("60/minute")
async def get_stats(request: Request) -> Envelope[StatsResponse]:
    raise _NOT_IMPLEMENTED


# 6. Detailer benchmarks ────────────────────────────────────────────────


@router.get(
    "/stats/detailer-benchmarks",
    response_model=Envelope[DetailerBenchmarksResponse],
)
@limiter.limit("60/minute")
async def get_detailer_benchmarks(
    request: Request,
) -> Envelope[DetailerBenchmarksResponse]:
    raise _NOT_IMPLEMENTED


# 7. Contact ────────────────────────────────────────────────────────────


@router.post(
    "/contact",
    response_model=Envelope[ContactResponse],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/minute")
async def submit_contact(
    request: Request,
    body: ContactRequest,
) -> Envelope[ContactResponse]:
    raise _NOT_IMPLEMENTED


# 8. Waitlist join ──────────────────────────────────────────────────────


@router.post(
    "/waitlist/join",
    response_model=Envelope[WaitlistJoinResponse],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/minute")
async def join_waitlist(
    request: Request,
    body: WaitlistJoinRequest,
) -> Envelope[WaitlistJoinResponse]:
    raise _NOT_IMPLEMENTED


# 9. Waitlist count ─────────────────────────────────────────────────────


@router.get("/waitlist/count", response_model=Envelope[WaitlistCountResponse])
@limiter.limit("30/minute")
async def get_waitlist_count(request: Request) -> Envelope[WaitlistCountResponse]:
    raise _NOT_IMPLEMENTED
