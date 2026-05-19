"""
domains/public/service.py — Business logic for Plan 19 (no SQL allowed).

Per AGENTS.md service-layer rules:
  - No SQL queries — always go through `PublicRepository`.
  - No HTTP calls or direct cross-service invocations.
  - Transaction-safe — wrap mutations in `async with session.begin()`.
  - Return typed Pydantic models, not dicts.
"""
from __future__ import annotations

from domains.public.models import FaqCategory, TestimonialRole
from domains.public.repository import PublicRepository
from domains.public.schemas import (
    ContactRequest,
    ContactResponse,
    CoverageCheckRequest,
    CoverageCheckResponse,
    CoverageZoneOut,
    CoverageZonesResponse,
    DetailerBenchmarksResponse,
    FaqItemOut,
    FaqResponse,
    StatsResponse,
    SvgCircle,
    TestimonialOut,
    TestimonialsResponse,
    WaitlistCountResponse,
    WaitlistJoinRequest,
    WaitlistJoinResponse,
)


# How many active mechanic-waitlist signups land per week, on average.
# Used to translate the raw `count` returned by the repository into a
# user-facing "X weeks" wait estimate on MechHero. Conservative
# placeholder — refine when we have real cohort throughput data.
_WAITLIST_AVG_SIGNUPS_PER_WEEK = 80


class PublicService:
    def __init__(self, repository: PublicRepository) -> None:
        self.repository = repository

    async def list_testimonials(
        self,
        *,
        role: TestimonialRole | None,
        featured: bool | None,
        limit: int,
    ) -> TestimonialsResponse:
        rows = await self.repository.list_testimonials(
            role=role, featured=featured, limit=limit,
        )
        return TestimonialsResponse(
            testimonials=[TestimonialOut.model_validate(r) for r in rows],
        )

    async def list_faq(self, *, category: FaqCategory | None) -> FaqResponse:
        rows = await self.repository.list_faq(category=category)
        return FaqResponse(
            faq=[FaqItemOut.model_validate(r) for r in rows],
        )

    async def list_coverage_zones(self) -> CoverageZonesResponse:
        rows = await self.repository.list_coverage_zones()
        return CoverageZonesResponse(
            zones=[
                CoverageZoneOut(
                    name=z.name,
                    is_primary=z.is_primary,
                    svg=SvgCircle(cx=z.svg_cx, cy=z.svg_cy, r=z.svg_r),
                )
                for z in rows
            ],
        )

    async def check_coverage(
        self, body: CoverageCheckRequest,
    ) -> CoverageCheckResponse:
        row = await self.repository.get_coverage_zip(body.zip)
        if row is None:
            return CoverageCheckResponse(covered=False, eta_at_launch=None, zone=None)
        eta_label = f"~{row.eta_min} min" if row.eta_min is not None else None
        return CoverageCheckResponse(
            covered=True, eta_at_launch=eta_label, zone=row.zone_name,
        )

    async def get_stats(self) -> StatsResponse:
        raise NotImplementedError

    async def get_detailer_benchmarks(self) -> DetailerBenchmarksResponse:
        raise NotImplementedError

    async def submit_contact(
        self,
        body: ContactRequest,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> ContactResponse:
        raise NotImplementedError

    async def join_waitlist(self, body: WaitlistJoinRequest) -> WaitlistJoinResponse:
        raise NotImplementedError

    async def get_waitlist_count(self) -> WaitlistCountResponse:
        count = await self.repository.count_waitlist_entries()
        weeks = max(1, (count + _WAITLIST_AVG_SIGNUPS_PER_WEEK - 1) // _WAITLIST_AVG_SIGNUPS_PER_WEEK)
        return WaitlistCountResponse(count=count, avg_wait_weeks=f"{weeks} weeks")
