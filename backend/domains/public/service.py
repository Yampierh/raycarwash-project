"""
domains/public/service.py — Business logic for Plan 19 (no SQL allowed).

Stub for Paso 3. Method signatures define the contract between router
and repository; bodies land in subsequent commits.

Per AGENTS.md service-layer rules:
  - No SQL queries — always go through `PublicRepository`.
  - No HTTP calls or direct cross-service invocations.
  - Transaction-safe — wrap mutations in `async with session.begin()`.
  - Return typed objects (Pydantic), not dicts.
"""
from __future__ import annotations

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
from domains.public.models import FaqCategory, TestimonialRole


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
        raise NotImplementedError

    async def list_faq(self, *, category: FaqCategory | None) -> FaqResponse:
        raise NotImplementedError

    async def list_coverage_zones(self) -> CoverageZonesResponse:
        raise NotImplementedError

    async def check_coverage(self, body: CoverageCheckRequest) -> CoverageCheckResponse:
        raise NotImplementedError

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
        """Inserts the row, enforces the 20/day/email cap, fires the
        internal notification (email or queue task — adapter TBD)."""
        raise NotImplementedError

    async def join_waitlist(self, body: WaitlistJoinRequest) -> WaitlistJoinResponse:
        """Returns 409 (via BusinessError) if email already on the waitlist."""
        raise NotImplementedError

    async def get_waitlist_count(self) -> WaitlistCountResponse:
        raise NotImplementedError
