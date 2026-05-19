"""
domains/public/repository.py — Async SQL access for Plan 19 endpoints.

Per AGENTS.md backend conventions:
  - Async SQLAlchemy 2.0 — `select()`, `await session.execute()`.
  - Always filter `is_deleted = False` for soft-delete-aware tables.
  - Return domain models or typed results, never dicts.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.public.models import (
    ContactSubmission,
    CoverageZip,
    CoverageZone,
    FaqCategory,
    FaqItem,
    Testimonial,
    TestimonialRole,
    WaitlistEntry,
    WaitlistRole,
)


class PublicRepository:
    """One repository for all Plan 19 reads/writes. The surface is small
    enough that splitting per-entity would be over-modular."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Testimonials ──────────────────────────────────────────────

    async def list_testimonials(
        self,
        *,
        role: TestimonialRole | None = None,
        featured: bool | None = None,
        limit: int = 10,
    ) -> list[Testimonial]:
        stmt = (
            select(Testimonial)
            .where(
                Testimonial.is_deleted.is_(False),
                Testimonial.is_active.is_(True),
            )
            .order_by(Testimonial.sort_order, Testimonial.created_at)
            .limit(limit)
        )
        if role is not None:
            stmt = stmt.where(Testimonial.role == role)
        if featured is True:
            stmt = stmt.where(Testimonial.featured.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── FAQ ───────────────────────────────────────────────────────

    async def list_faq(
        self,
        *,
        category: FaqCategory | None = None,
    ) -> list[FaqItem]:
        stmt = (
            select(FaqItem)
            .where(
                FaqItem.is_deleted.is_(False),
                FaqItem.is_active.is_(True),
            )
            .order_by(FaqItem.category, FaqItem.sort_order)
        )
        if category is not None:
            stmt = stmt.where(FaqItem.category == category)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Coverage zones / ZIP lookup ───────────────────────────────

    async def list_coverage_zones(self) -> list[CoverageZone]:
        stmt = (
            select(CoverageZone)
            .where(
                CoverageZone.is_deleted.is_(False),
                CoverageZone.is_active.is_(True),
            )
            .order_by(CoverageZone.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_coverage_zip(self, zip_code: str) -> CoverageZip | None:
        stmt = select(CoverageZip).where(
            CoverageZip.zip == zip_code,
            CoverageZip.is_deleted.is_(False),
            CoverageZip.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Aggregate stats ───────────────────────────────────────────

    async def fetch_stats_snapshot(self) -> dict:
        """Returns a dict matching `StatsResponse` fields. Pulls from the
        live `appointments`, `provider_profiles`, and `reviews` tables
        via cheap COUNT/AVG aggregates with results cached at the
        service layer (1h TTL per Plan 19 §10.2)."""
        raise NotImplementedError

    async def fetch_detailer_benchmarks(self) -> dict:
        """Static-config initially. Later: percentile aggregation over
        `provider_earnings`."""
        raise NotImplementedError

    # ── Contact submissions ───────────────────────────────────────

    async def create_contact_submission(
        self,
        *,
        name: str,
        email: str,
        subject: str | None,
        message: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ContactSubmission:
        raise NotImplementedError

    async def count_contact_submissions_by_email_since(
        self, email: str, hours: int = 24,
    ) -> int:
        """Used by the service layer to enforce the "20/day per email"
        sub-limit in Plan 19 §10.1 (the IP rate limit handles raw abuse;
        this one catches distributed spam from the same submitter)."""
        raise NotImplementedError

    # ── Waitlist ──────────────────────────────────────────────────

    async def create_waitlist_entry(
        self,
        *,
        email: str,
        role: WaitlistRole,
    ) -> WaitlistEntry:
        """Raises sqlalchemy IntegrityError on UNIQUE(email) collision —
        service layer translates to 409 Conflict."""
        raise NotImplementedError

    async def count_waitlist_entries(
        self, role: WaitlistRole | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(WaitlistEntry)
            .where(WaitlistEntry.is_deleted.is_(False))
        )
        if role is not None:
            stmt = stmt.where(WaitlistEntry.role == role)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_waitlist_entry_by_email(self, email: str) -> WaitlistEntry | None:
        raise NotImplementedError
