"""
domains/public/models.py — SQLAlchemy models for Plan 19 (marketing).

Six tables, all soft-delete compatible via TimestampMixin (per AGENTS.md
"Soft deletes on every entity. Always filter. Never hard-delete.").

Tables:
  testimonials         — quotes by clients/detailers used on landing pages.
  faq                  — Q&A grouped by audience (rider/detailer/mechanic/provider).
  coverage_zones       — service area circles for the SVG map on Landing.tsx.
  coverage_zips        — ZIP → zone mapping for POST /coverage/check.
                         PK is the ZIP itself; no surrogate UUID.
  contact_submissions  — append-only inbox for the public contact form.
  waitlist_entries     — append-only waitlist (mechanic vertical, future expansion).
                         Email is UNIQUE — duplicate signups return 409.

The actual schema lives in Alembic migrations (m_018+). create_all() in
dev/test reads these models; production runs `alembic upgrade head`.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base, TimestampMixin


# ─── Enums ─────────────────────────────────────────────────────────────


class TestimonialRole(str, enum.Enum):
    CLIENT   = "client"
    DETAILER = "detailer"


class FaqCategory(str, enum.Enum):
    RIDER    = "rider"
    DETAILER = "detailer"
    MECHANIC = "mechanic"
    PROVIDER = "provider"


class WaitlistRole(str, enum.Enum):
    MECHANIC = "mechanic"
    DETAILER = "detailer"
    PROVIDER = "provider"


# ─── Tables ────────────────────────────────────────────────────────────


class Testimonial(TimestampMixin, Base):
    """Marketing quote shown on Landing.tsx, Customer.tsx, Detailers.tsx.

    Filtering knobs:
      - `role`: CLIENT vs DETAILER (Testimonials block vs DetTestimonials block).
      - `featured`: only featured items shown on Hero/landing.
      - `sort_order`: explicit display order within a category.
    """

    __tablename__ = "testimonials"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_testimonials_rating_range"),
        Index("ix_testimonials_role_featured", "role", "featured", "is_deleted"),
        Index("ix_testimonials_sort", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    role: Mapped[TestimonialRole] = mapped_column(
        Enum(TestimonialRole, name="testimonial_role_enum"), nullable=False,
    )
    # Optional descriptor like "Detailer · 312 jobs · ★ 4.9"
    meta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Testimonial id={self.id} role={self.role.value} featured={self.featured}>"


class FaqItem(TimestampMixin, Base):
    """One row per Q&A across rider/detailer/mechanic/provider pages."""

    __tablename__ = "faq"
    __table_args__ = (
        Index("ix_faq_category_sort", "category", "sort_order", "is_deleted"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    category: Mapped[FaqCategory] = mapped_column(
        Enum(FaqCategory, name="faq_category_enum"), nullable=False,
    )
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<FaqItem id={self.id} category={self.category.value}>"


class CoverageZone(TimestampMixin, Base):
    """Named service zone for the SVG coverage map on Landing.tsx.

    `svg_cx`, `svg_cy`, `svg_r` are coordinates inside a 100×100 viewBox
    (per the prototype in `raycarwash/project/`). Primary zone (Fort Wayne)
    has `is_primary=True` and is rendered larger.
    """

    __tablename__ = "coverage_zones"
    __table_args__ = (
        Index("ix_coverage_zones_active_primary", "is_active", "is_primary"),
        Index("ix_coverage_zones_sort", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    svg_cx: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    svg_cy: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    svg_r: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<CoverageZone name={self.name} primary={self.is_primary}>"


class CoverageZip(TimestampMixin, Base):
    """ZIP → zone mapping for POST /coverage/check.

    PK is the ZIP itself (no surrogate UUID) — natural identifier, no two
    entries for the same ZIP can co-exist active.
    """

    __tablename__ = "coverage_zips"
    __table_args__ = (
        Index("ix_coverage_zips_zone", "zone_name", "is_active"),
    )

    zip: Mapped[str] = mapped_column(String(5), primary_key=True)
    zone_name: Mapped[str] = mapped_column(String(120), nullable=False)
    eta_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<CoverageZip zip={self.zip} zone={self.zone_name}>"


class ContactSubmission(TimestampMixin, Base):
    """Append-only inbox for the public contact form. Each row triggers
    an internal notification email to the support team (handled in the
    service layer, not on insert)."""

    __tablename__ = "contact_submissions"
    __table_args__ = (
        Index("ix_contact_submissions_email_created", "email", "created_at"),
        Index("ix_contact_submissions_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # PostgreSQL INET type — null on tests that don't have a client IP.
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<ContactSubmission id={self.id} email={self.email}>"


class WaitlistEntry(TimestampMixin, Base):
    """Append-only waitlist for the mechanic vertical (and future roles).

    `email` is UNIQUE — duplicate signups return 409 per Plan 19 §8.
    `position` is denormalized at insert time (current count + 1); not
    auto-maintained on soft delete, which is acceptable for the initial
    rollout (the public count is approximate).
    """

    __tablename__ = "waitlist_entries"
    __table_args__ = (
        UniqueConstraint("email", name="uq_waitlist_entries_email"),
        Index("ix_waitlist_entries_role_created", "role", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[WaitlistRole] = mapped_column(
        Enum(WaitlistRole, name="waitlist_role_enum"),
        nullable=False,
        default=WaitlistRole.MECHANIC,
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<WaitlistEntry id={self.id} email={self.email} role={self.role.value}>"
