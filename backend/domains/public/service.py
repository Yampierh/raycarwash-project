"""
domains/public/service.py — Business logic for Plan 19 (no SQL allowed).

Per AGENTS.md service-layer rules:
  - No SQL queries — always go through `PublicRepository`.
  - No HTTP calls or direct cross-service invocations.
  - Transaction-safe — wrap mutations in `async with session.begin()`.
  - Return typed Pydantic models, not dicts.
"""
from __future__ import annotations

from fastapi import status
from sqlalchemy.exc import IntegrityError

from app.exception_handlers import BusinessError
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


# Per-email anti-spam cap on the contact form. The slowapi rate limit
# in §10.1 (`3/min per IP`) blunts raw abuse, but a distributed actor
# rotating IPs while reusing one email could still overwhelm support.
# This cap fires a 429 once the same email has submitted 20 messages
# in the last 24 hours.
_CONTACT_MAX_PER_EMAIL_PER_DAY = 20
_CONTACT_WINDOW_HOURS = 24


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
        # Per-email cap. Pydantic normalised email to lowercase already.
        count = await self.repository.count_contact_submissions_by_email_since(
            body.email, hours=_CONTACT_WINDOW_HOURS,
        )
        if count >= _CONTACT_MAX_PER_EMAIL_PER_DAY:
            raise BusinessError(
                code="rate_limit_exceeded",
                message=(
                    f"This email has reached the daily contact-form limit "
                    f"({_CONTACT_MAX_PER_EMAIL_PER_DAY} submissions in the last "
                    f"{_CONTACT_WINDOW_HOURS} hours). Try again later."
                ),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        row = await self.repository.create_contact_submission(
            name=body.name,
            email=body.email,
            subject=body.subject,
            message=body.message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return ContactResponse(id=row.id, status="received")

    async def join_waitlist(self, body: WaitlistJoinRequest) -> WaitlistJoinResponse:
        # Fast-path: existing email lookup avoids the DB IntegrityError
        # round-trip for the duplicate-signup case (common — same user
        # tapping "join" twice). The repo still races behind a UNIQUE
        # constraint that catches concurrent inserts.
        existing = await self.repository.get_waitlist_entry_by_email(body.email)
        if existing is not None:
            raise BusinessError(
                code="email_already_on_waitlist",
                message="This email is already on the waitlist.",
                status_code=status.HTTP_409_CONFLICT,
            )

        # Position is `count_before_insert + 1`. The COUNT excludes
        # soft-deleted rows so position numbers stay stable even if an
        # admin prunes the list later. Concurrent inserts may produce
        # duplicate positions — acceptable per Plan 19 §8 ("position is
        # approximate") and worth less than the SELECT FOR UPDATE
        # serialization overhead.
        next_position = await self.repository.count_waitlist_entries() + 1

        try:
            row = await self.repository.create_waitlist_entry(
                email=body.email, role=body.role, position=next_position,
            )
        except IntegrityError:
            # Lost the race against another concurrent insert with the
            # same email. Same 409 as the fast-path check above.
            raise BusinessError(
                code="email_already_on_waitlist",
                message="This email is already on the waitlist.",
                status_code=status.HTTP_409_CONFLICT,
            )

        return WaitlistJoinResponse(id=row.id, position=row.position or next_position)

    async def get_waitlist_count(self) -> WaitlistCountResponse:
        count = await self.repository.count_waitlist_entries()
        weeks = max(1, (count + _WAITLIST_AVG_SIGNUPS_PER_WEEK - 1) // _WAITLIST_AVG_SIGNUPS_PER_WEEK)
        return WaitlistCountResponse(count=count, avg_wait_weeks=f"{weeks} weeks")
