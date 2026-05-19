"""
domains/public/repository.py — Async SQL access for Plan 19 endpoints.

Stub for Paso 3. Method signatures are fixed (the service layer +
contract code can reference them once implemented) but each body raises
NotImplementedError. Implementations land in Paso 4+ alongside seed
data and end-to-end tests.

Conventions (per AGENTS.md):
  - Async SQLAlchemy 2.0 — `select()`, `await session.execute()`.
  - Always filter `is_deleted = False`.
  - Return domain models or typed results, never dicts.
"""
from __future__ import annotations

import uuid

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
        raise NotImplementedError

    # ── FAQ ───────────────────────────────────────────────────────

    async def list_faq(self, *, category: FaqCategory | None = None) -> list[FaqItem]:
        raise NotImplementedError

    # ── Coverage zones / ZIP lookup ───────────────────────────────

    async def list_coverage_zones(self) -> list[CoverageZone]:
        raise NotImplementedError

    async def get_coverage_zip(self, zip_code: str) -> CoverageZip | None:
        raise NotImplementedError

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

    async def count_waitlist_entries(self, role: WaitlistRole | None = None) -> int:
        raise NotImplementedError

    async def get_waitlist_entry_by_email(self, email: str) -> WaitlistEntry | None:
        raise NotImplementedError
