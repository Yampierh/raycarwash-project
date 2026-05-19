"""
domains/public/repository.py — Async SQL access for Plan 19 endpoints.

Per AGENTS.md backend conventions:
  - Async SQLAlchemy 2.0 — `select()`, `await session.execute()`.
  - Always filter `is_deleted = False` for soft-delete-aware tables.
  - Return domain models or typed results, never dicts.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
        """Returns the four DB-derived metrics for `GET /public/stats`:
        completed deliveries, average review rating, active detailer
        count, and total review count. The two remaining
        `StatsResponse` fields (avg_eta_min, median_earnings_per_hr)
        live in the service layer as static placeholders until we have
        the earnings + assignment-timing data to compute them.

        Soft-delete-filtered. COALESCE(AVG, 0) so a fresh DB doesn't
        return NULL where the schema requires a number.
        """
        from domains.appointments.models import Appointment, AppointmentStatus
        from domains.providers.models import ProviderProfile
        from domains.reviews.models import Review

        deliveries_q = (
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.is_deleted.is_(False),
            )
        )
        avg_rating_q = (
            select(func.coalesce(func.avg(Review.rating), 0.0))
            .select_from(Review)
            .where(Review.is_deleted.is_(False))
        )
        active_detailers_q = (
            select(func.count())
            .select_from(ProviderProfile)
            .where(
                ProviderProfile.is_active.is_(True),
                ProviderProfile.is_deleted.is_(False),
            )
        )
        total_reviews_q = (
            select(func.count())
            .select_from(Review)
            .where(Review.is_deleted.is_(False))
        )

        deliveries = int((await self.session.execute(deliveries_q)).scalar_one())
        avg_rating = float((await self.session.execute(avg_rating_q)).scalar_one())
        active_detailers = int((await self.session.execute(active_detailers_q)).scalar_one())
        total_reviews = int((await self.session.execute(total_reviews_q)).scalar_one())

        return {
            "deliveries": deliveries,
            "avg_rating": round(avg_rating, 2),
            "active_detailers": active_detailers,
            "total_reviews": total_reviews,
        }

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
        row = ContactSubmission(
            name=name,
            email=email,
            subject=subject,
            message=message,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def count_contact_submissions_by_email_since(
        self, email: str, hours: int = 24,
    ) -> int:
        """Used by the service layer to enforce the "20/day per email"
        sub-limit in Plan 19 §10.1 (the IP rate limit handles raw abuse;
        this one catches distributed spam from the same submitter).

        Soft-deleted rows are counted intentionally — an admin soft-deleting
        a submission shouldn't reset the abuse window.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(func.count())
            .select_from(ContactSubmission)
            .where(
                ContactSubmission.email == email,
                ContactSubmission.created_at >= since,
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    # ── Waitlist ──────────────────────────────────────────────────

    async def create_waitlist_entry(
        self,
        *,
        email: str,
        role: WaitlistRole,
        position: int | None = None,
    ) -> WaitlistEntry:
        """Inserts a waitlist row. Raises sqlalchemy.exc.IntegrityError on
        UNIQUE(email) collision — the service layer catches and translates
        to a 409 Conflict via BusinessError."""
        row = WaitlistEntry(email=email, role=role, position=position)
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return row

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
        stmt = select(WaitlistEntry).where(
            WaitlistEntry.email == email,
            WaitlistEntry.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
