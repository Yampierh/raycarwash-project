"""
domains/public/schemas.py — Pydantic shapes for Plan 19 endpoints.

Contract source: docs/plans/19-api-contracts-track1-marketing.md
Validation constraints: §10.4 (max_length + strip + EmailStr normalization).

All response schemas inherit from `_BaseSchema` so they read from ORM
attributes (from_attributes=True). Request schemas inherit from
`_BaseRequestSchema` so input strings are stripped on parse.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field, field_validator

from domains.public.models import FaqCategory, TestimonialRole, WaitlistRole
from shared.schemas import _BaseRequestSchema, _BaseSchema


# ═══════════════════════════════════════════════════════════════════════
#  1. GET /api/v1/public/testimonials
# ═══════════════════════════════════════════════════════════════════════


class TestimonialOut(_BaseSchema):
    id: uuid.UUID
    quote: str
    name: str
    city: str | None = None
    rating: int = Field(..., ge=1, le=5)
    role: TestimonialRole
    meta: str | None = None
    featured: bool
    sort_order: int
    created_at: datetime


class TestimonialsResponse(_BaseSchema):
    testimonials: list[TestimonialOut]


# ═══════════════════════════════════════════════════════════════════════
#  2. GET /api/v1/public/faq
# ═══════════════════════════════════════════════════════════════════════


class FaqItemOut(_BaseSchema):
    id: uuid.UUID
    category: FaqCategory
    question: str
    answer: str
    sort_order: int


class FaqResponse(_BaseSchema):
    faq: list[FaqItemOut]


# ═══════════════════════════════════════════════════════════════════════
#  3. GET /api/v1/public/coverage-zones
# ═══════════════════════════════════════════════════════════════════════


class SvgCircle(_BaseSchema):
    cx: int
    cy: int
    r: int


class CoverageZoneOut(_BaseSchema):
    name: str
    is_primary: bool
    svg: SvgCircle


class CoverageZonesResponse(_BaseSchema):
    zones: list[CoverageZoneOut]


# ═══════════════════════════════════════════════════════════════════════
#  4. POST /api/v1/public/coverage/check
# ═══════════════════════════════════════════════════════════════════════


class CoverageCheckRequest(_BaseRequestSchema):
    # 5-digit US ZIP, no ZIP+4 yet. Regex enforces digits-only.
    zip: str = Field(..., min_length=5, max_length=5, pattern=r"^\d{5}$")


class CoverageCheckResponse(_BaseSchema):
    covered: bool
    # Free-form ETA string ("~22 min" at launch). Null when uncovered.
    eta_at_launch: str | None = None
    zone: str | None = None


# ═══════════════════════════════════════════════════════════════════════
#  5. GET /api/v1/public/stats
# ═══════════════════════════════════════════════════════════════════════


class StatsResponse(_BaseSchema):
    """Aggregated marketing metrics. Values are *rounded approximations*
    refreshed on a worker schedule — Plan 22 H6 mitigation against
    competitor scraping of real-time business volume."""

    deliveries: int
    deliveries_label: str
    avg_eta_min: int
    avg_eta_label: str
    avg_rating: float
    avg_rating_label: str
    active_detailers: int
    active_detailers_label: str
    median_earnings_per_hr: int
    median_earnings_label: str
    total_reviews: int
    total_reviews_label: str


# ═══════════════════════════════════════════════════════════════════════
#  6. GET /api/v1/public/stats/detailer-benchmarks
# ═══════════════════════════════════════════════════════════════════════


class DetailerBenchmarksResponse(_BaseSchema):
    """Marketing-approved earnings benchmarks for detailer recruitment.
    Static config at launch; later replaced with real-aggregated values.

    All `*_weekly` and `avg_per_job` fields are **integer cents** per
    the AGENTS.md project convention (`median_weekly=184_000` = $1,840).
    The accompanying `*_label` strings are pre-formatted for display
    so the portal doesn't have to choose a locale at render time.
    """

    median_weekly: int
    median_weekly_label: str
    top_quartile_weekly: int
    top_quartile_weekly_label: str
    top_10pct_weekly: int
    top_10pct_weekly_label: str
    avg_per_job: int
    avg_per_job_label: str


# ═══════════════════════════════════════════════════════════════════════
#  7. POST /api/v1/public/contact
# ═══════════════════════════════════════════════════════════════════════


class ContactRequest(_BaseRequestSchema):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr = Field(..., max_length=320)
    subject: str | None = Field(default=None, max_length=255)
    message: str = Field(..., min_length=1, max_length=5000)

    @field_validator("email", mode="after")
    @classmethod
    def _lowercase_email(cls, v: str) -> str:
        # Normalize per Plan 19 §10.4 — prevents case-mismatched duplicates.
        return v.lower()


class ContactResponse(_BaseSchema):
    id: uuid.UUID
    status: Literal["received"] = "received"


# ═══════════════════════════════════════════════════════════════════════
#  8. POST /api/v1/public/waitlist/join
# ═══════════════════════════════════════════════════════════════════════


class WaitlistJoinRequest(_BaseRequestSchema):
    email: EmailStr = Field(..., max_length=320)
    role: WaitlistRole = WaitlistRole.MECHANIC

    @field_validator("email", mode="after")
    @classmethod
    def _lowercase_email(cls, v: str) -> str:
        return v.lower()


class WaitlistJoinResponse(_BaseSchema):
    id: uuid.UUID
    position: int


# ═══════════════════════════════════════════════════════════════════════
#  9. GET /api/v1/public/waitlist/count
# ═══════════════════════════════════════════════════════════════════════


class WaitlistCountResponse(_BaseSchema):
    count: int
    # Free-form text ("4 weeks") — displayed verbatim on MechHero.
    avg_wait_weeks: str
