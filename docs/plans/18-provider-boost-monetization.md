# 18 — Provider Boost & Monetization System

> **Status:** Planning · production-ready blueprint
> **Priority:** High (revenue-generating)
> **Dependencies:** `09-provider-services-integration.md` (provider services), `11-provider-dashboard.md` (dashboard surfaces these), `10-authorization-layer.md` (provider scope)
> **Audit findings resolved:** N/A (new revenue surface)
> **Owner domain:** `backend/domains/boosts/`

---

## 1. Objective

Introduce a **monetization layer** on top of the existing marketplace so providers can pay to:

1. **Boost their search ranking** for a bounded window (the `search_boost` lever).
2. **Feature a specific service** so it surfaces above their other services.
3. **Receive data-driven recommendations** ("Insights Engine") that explain *why* a boost makes sense for them right now.

Design constraints:
- **Financially correct**: every charge maps to a ledger entry; refunds are first-class.
- **Scalable to thousands of providers**: ranking query stays sub-100 ms with indexed joins.
- **Extensible**: ranking score is a pure function; future levers (auctions, subscriptions, sponsored slots) plug in without rewrites.
- **Abuse-resistant**: one active boost per type per provider; FSM-locked transitions; idempotency on purchase.
- **Reusable ranking**: the same `compute_provider_score()` is consumed by search, matching, and the Provider Dashboard's "your current rank" widget.

Surfaced in the Provider Dashboard under a new tab **"Boosts & Visibility"** (see `web/dashboard/boosts/` in plan 11).

---

## 2. Architecture overview

```
domains/boosts/
├── __init__.py
├── models.py          # ProviderBoost, FeaturedService, BoostInvoice, DemandSnapshot
├── repository.py      # All DB I/O (no service logic)
├── service.py         # Business rules: purchase, expire, score, insights
├── pricing.py         # Pure functions: base price, demand multiplier, duration cost
├── ranking.py         # compute_provider_score() — used by search + matching
├── insights.py        # Insights Engine heuristics
├── payment_gateway.py # Abstract payment interface (Stripe-ready, sim impl today)
├── schemas.py         # Pydantic v2 request/response schemas
├── router.py          # /api/v1/provider/* endpoints
└── tasks.py           # Background worker entry (expiration sweep)
```

External touch-points:
- `infrastructure/db/registry.py` — registers new models so SQLAlchemy + Alembic see them.
- `api/router.py` — mounts `domains.boosts.router`.
- `domains/matching/service.py` — calls `compute_provider_score()` in the candidate-ranking stage.
- `workers/` — schedules `tasks.expire_boosts_sweep()` every minute.

---

## 3. Domain model

### 3.1 SQLAlchemy models — `backend/domains/boosts/models.py`

```python
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index,
    Integer, Numeric, String, Text, UniqueConstraint, func, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base, TimestampMixin


class BoostType(str, enum.Enum):
    """
    Kinds of paid visibility levers. New verticals (sponsored_slot,
    category_takeover, etc.) extend this enum without a migration —
    the column is VARCHAR, not a PG enum.
    """
    SEARCH_BOOST = "search_boost"


class BoostStatus(str, enum.Enum):
    """
    FSM:  pending_payment → active → (expired | cancelled | refunded)
    Only `active` boosts affect ranking. `pending_payment` exists for
    the gap between purchase intent and gateway confirmation.
    """
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class DemandLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProviderBoost(TimestampMixin, Base):
    """
    A time-bounded ranking multiplier purchased by a provider.

    Invariant (enforced via unique partial index): at most ONE row with
    status='active' per (provider_user_id, type). The DB rejects concurrent
    purchases instead of trusting application-layer checks.
    """
    __tablename__ = "provider_boosts"
    __table_args__ = (
        # Partial unique: only one *active* boost per (provider, type).
        # PG-specific — created via op.execute() in migration.
        Index(
            "uq_provider_boosts_active_per_type",
            "provider_user_id", "type",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        # Hot path for ranking: fetch active boost by provider.
        Index(
            "ix_provider_boosts_active_lookup",
            "provider_user_id", "status", "expires_at",
        ),
        # Worker sweep: find boosts whose expires_at has passed.
        Index(
            "ix_provider_boosts_expires_status",
            "expires_at", "status",
        ),
        CheckConstraint(
            "multiplier >= 1.0 AND multiplier <= 5.0",
            name="ck_provider_boosts_multiplier_range",
        ),
        CheckConstraint(
            "expires_at > starts_at",
            name="ck_provider_boosts_expires_after_start",
        ),
        CheckConstraint(
            "price_cents >= 0",
            name="ck_provider_boosts_price_nonneg",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        server_default=BoostType.SEARCH_BOOST.value,
    )
    multiplier: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="1.0"
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        server_default=BoostStatus.PENDING_PAYMENT.value,
    )
    # Snapshot of pricing inputs at purchase time. Lets us audit later.
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    base_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    demand_multiplier_applied: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="1.0"
    )
    demand_level_at_purchase: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=DemandLevel.MEDIUM.value
    )
    # Free-form context (impressions snapshot, idempotency key, etc.)
    metadata_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    # Foreign key to the invoice / payment intent. Nullable to support
    # admin-issued comp boosts that never flow through the gateway.
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("boost_invoices.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    provider: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[provider_user_id], lazy="joined"
    )
    invoice: Mapped["BoostInvoice | None"] = relationship(
        "BoostInvoice", foreign_keys=[invoice_id], lazy="select"
    )


class FeaturedService(TimestampMixin, Base):
    """
    Highlights a single (provider, service) pair for a bounded window.

    Constraint: at most ONE *active* featured row per (provider, service).
    Multiple services per provider can be featured concurrently — this is
    intentional: providers may feature their flagship + a seasonal offer.
    """
    __tablename__ = "featured_services"
    __table_args__ = (
        Index(
            "uq_featured_services_active_per_pair",
            "provider_user_id", "service_id",
            unique=True,
            postgresql_where=text("expires_at > NOW()"),
        ),
        Index(
            "ix_featured_services_expires_at",
            "expires_at",
        ),
        Index(
            "ix_featured_services_provider_active",
            "provider_user_id", "expires_at",
        ),
        CheckConstraint(
            "expires_at > starts_at",
            name="ck_featured_services_expires_after_start",
        ),
        CheckConstraint(
            "price_cents >= 0",
            name="ck_featured_services_price_nonneg",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("boost_invoices.id", ondelete="SET NULL"),
        nullable=True,
    )


class BoostInvoice(TimestampMixin, Base):
    """
    Financial record for every boost / featured purchase. One invoice can
    pay for one boost. Refunds reverse the invoice and emit a `LedgerEntry`
    (plan 11 §4) of kind `adjustment`.

    Idempotency key is stored at the invoice level so retried POSTs return
    the same boost without double-charging.
    """
    __tablename__ = "boost_invoices"
    __table_args__ = (
        UniqueConstraint(
            "provider_user_id", "idempotency_key",
            name="uq_boost_invoices_idempotency",
        ),
        Index(
            "ix_boost_invoices_provider_status",
            "provider_user_id", "status",
        ),
        CheckConstraint(
            "amount_cents >= 0",
            name="ck_boost_invoices_amount_nonneg",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # 'boost' | 'featured'
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, server_default="USD"
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default="pending"
    )  # pending | succeeded | failed | refunded
    payment_gateway: Mapped[str] = mapped_column(
        String(24), nullable=False, server_default="simulated"
    )  # stripe | simulated | comp
    gateway_intent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gateway_charge_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    succeeded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )


class DemandSnapshot(Base):
    """
    Rolling metro/category demand index. Written every 15 minutes by a
    background worker that samples recent booking velocity vs. provider
    supply. Read by the Insights Engine + pricing to set demand multiplier.

    Bounded retention (90 days) — older rows pruned by a sweep.
    """
    __tablename__ = "demand_snapshots"
    __table_args__ = (
        Index(
            "ix_demand_snapshots_metro_window",
            "metro_slug", "window_start",
        ),
        UniqueConstraint(
            "metro_slug", "service_category", "window_start",
            name="uq_demand_snapshot_window",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    metro_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    service_category: Mapped[str] = mapped_column(
        String(40), nullable=False, server_default="detailing"
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    bookings_count: Mapped[int] = mapped_column(Integer, nullable=False)
    impressions_count: Mapped[int] = mapped_column(Integer, nullable=False)
    active_providers: Mapped[int] = mapped_column(Integer, nullable=False)
    conversion_rate: Mapped[float] = mapped_column(Float, nullable=False)
    demand_level: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=DemandLevel.MEDIUM.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
```

> Models register in `infrastructure/db/registry.py` by adding `from domains.boosts import models  # noqa: F401` near the other domain imports.

---

## 4. Alembic migration — `backend/alembic/versions/m_018_provider_boosts.py`

```python
"""Provider boosts, featured services, invoices, demand snapshots.

Revision ID: m_018_provider_boosts
Revises: m_017_drop_is_accepting_bookings
Create Date: 2026-05-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "m_018_provider_boosts"
down_revision = "m_017_drop_is_accepting_bookings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── boost_invoices ──────────────────────────────────────────────────
    op.create_table(
        "boost_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending"),
        sa.Column("payment_gateway", sa.String(24), nullable=False, server_default="simulated"),
        sa.Column("gateway_intent_id", sa.String(128), nullable=True),
        sa.Column("gateway_charge_id", sa.String(128), nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("succeeded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_cents >= 0", name="ck_boost_invoices_amount_nonneg"),
        sa.UniqueConstraint("provider_user_id", "idempotency_key", name="uq_boost_invoices_idempotency"),
    )
    op.create_index(
        "ix_boost_invoices_provider_status",
        "boost_invoices",
        ["provider_user_id", "status"],
    )

    # ─── provider_boosts ─────────────────────────────────────────────────
    op.create_table(
        "provider_boosts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(40), nullable=False, server_default="search_boost"),
        sa.Column("multiplier", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="pending_payment"),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("base_price_cents", sa.Integer(), nullable=False),
        sa.Column("demand_multiplier_applied", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("demand_level_at_purchase", sa.String(16), nullable=False, server_default="medium"),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("boost_invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("multiplier >= 1.0 AND multiplier <= 5.0", name="ck_provider_boosts_multiplier_range"),
        sa.CheckConstraint("expires_at > starts_at", name="ck_provider_boosts_expires_after_start"),
        sa.CheckConstraint("price_cents >= 0", name="ck_provider_boosts_price_nonneg"),
    )
    op.create_index(
        "ix_provider_boosts_provider_user_id",
        "provider_boosts",
        ["provider_user_id"],
    )
    op.create_index(
        "ix_provider_boosts_active_lookup",
        "provider_boosts",
        ["provider_user_id", "status", "expires_at"],
    )
    op.create_index(
        "ix_provider_boosts_expires_status",
        "provider_boosts",
        ["expires_at", "status"],
    )
    # Partial unique: enforce single active boost per (provider, type).
    op.execute(
        "CREATE UNIQUE INDEX uq_provider_boosts_active_per_type "
        "ON provider_boosts (provider_user_id, type) "
        "WHERE status = 'active'"
    )

    # ─── featured_services ───────────────────────────────────────────────
    op.create_table(
        "featured_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("services.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("boost_invoices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("expires_at > starts_at", name="ck_featured_services_expires_after_start"),
        sa.CheckConstraint("price_cents >= 0", name="ck_featured_services_price_nonneg"),
    )
    op.create_index(
        "ix_featured_services_provider_user_id",
        "featured_services",
        ["provider_user_id"],
    )
    op.create_index(
        "ix_featured_services_service_id",
        "featured_services",
        ["service_id"],
    )
    op.create_index(
        "ix_featured_services_provider_active",
        "featured_services",
        ["provider_user_id", "expires_at"],
    )
    op.create_index(
        "ix_featured_services_expires_at",
        "featured_services",
        ["expires_at"],
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_featured_services_active_per_pair "
        "ON featured_services (provider_user_id, service_id) "
        "WHERE expires_at > NOW()"
    )

    # ─── demand_snapshots ────────────────────────────────────────────────
    op.create_table(
        "demand_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("metro_slug", sa.String(64), nullable=False),
        sa.Column("service_category", sa.String(40), nullable=False, server_default="detailing"),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bookings_count", sa.Integer(), nullable=False),
        sa.Column("impressions_count", sa.Integer(), nullable=False),
        sa.Column("active_providers", sa.Integer(), nullable=False),
        sa.Column("conversion_rate", sa.Float(), nullable=False),
        sa.Column("demand_level", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("metro_slug", "service_category", "window_start", name="uq_demand_snapshot_window"),
    )
    op.create_index(
        "ix_demand_snapshots_metro_slug",
        "demand_snapshots",
        ["metro_slug"],
    )
    op.create_index(
        "ix_demand_snapshots_metro_window",
        "demand_snapshots",
        ["metro_slug", "window_start"],
    )


def downgrade() -> None:
    op.drop_index("ix_demand_snapshots_metro_window", table_name="demand_snapshots")
    op.drop_index("ix_demand_snapshots_metro_slug", table_name="demand_snapshots")
    op.drop_table("demand_snapshots")

    op.execute("DROP INDEX IF EXISTS uq_featured_services_active_per_pair")
    op.drop_index("ix_featured_services_expires_at", table_name="featured_services")
    op.drop_index("ix_featured_services_provider_active", table_name="featured_services")
    op.drop_index("ix_featured_services_service_id", table_name="featured_services")
    op.drop_index("ix_featured_services_provider_user_id", table_name="featured_services")
    op.drop_table("featured_services")

    op.execute("DROP INDEX IF EXISTS uq_provider_boosts_active_per_type")
    op.drop_index("ix_provider_boosts_expires_status", table_name="provider_boosts")
    op.drop_index("ix_provider_boosts_active_lookup", table_name="provider_boosts")
    op.drop_index("ix_provider_boosts_provider_user_id", table_name="provider_boosts")
    op.drop_table("provider_boosts")

    op.drop_index("ix_boost_invoices_provider_status", table_name="boost_invoices")
    op.drop_table("boost_invoices")
```

---

## 5. Pricing — `backend/domains/boosts/pricing.py`

Pure functions, no DB. Inputs are explicit so unit tests don't need a session.

```python
from __future__ import annotations

from dataclasses import dataclass

from domains.boosts.models import DemandLevel


# Tuning knobs — exposed as constants so they can move to admin config
# (plan 15) without touching the rest of the system.
BASE_PRICE_CENTS_PER_HOUR = 99       # $0.99/hr base
DEMAND_MULTIPLIER = {
    DemandLevel.LOW: 0.80,
    DemandLevel.MEDIUM: 1.00,
    DemandLevel.HIGH: 1.35,
}
# Bulk-discount curve — encourages longer windows.
DURATION_DISCOUNT = [
    (6, 1.00),    # ≤6h: full price
    (24, 0.92),   # ≤24h: −8%
    (72, 0.85),   # ≤3d: −15%
    (168, 0.78),  # ≤1w: −22%
]
MIN_DURATION_HOURS = 1
MAX_DURATION_HOURS = 168  # 7 days
ALLOWED_MULTIPLIERS = (1.2, 1.5, 2.0)


@dataclass(frozen=True)
class PriceQuote:
    duration_hours: int
    multiplier: float
    demand_level: DemandLevel
    base_price_cents: int
    demand_multiplier_applied: float
    duration_discount_applied: float
    final_price_cents: int


def quote_boost_price(
    *,
    duration_hours: int,
    multiplier: float,
    demand_level: DemandLevel,
) -> PriceQuote:
    """
    Compute the price for a search boost. Pure function — no I/O.

    Pricing formula:
        base   = BASE_PRICE_CENTS_PER_HOUR * duration_hours * multiplier
        demand = base * DEMAND_MULTIPLIER[demand_level]
        final  = demand * DURATION_DISCOUNT[duration_bracket]

    Rounded to the nearest cent.
    """
    if duration_hours < MIN_DURATION_HOURS or duration_hours > MAX_DURATION_HOURS:
        raise ValueError(
            f"duration_hours must be in [{MIN_DURATION_HOURS}, {MAX_DURATION_HOURS}]"
        )
    if multiplier not in ALLOWED_MULTIPLIERS:
        raise ValueError(
            f"multiplier must be one of {ALLOWED_MULTIPLIERS}"
        )
    base = BASE_PRICE_CENTS_PER_HOUR * duration_hours * multiplier
    demand_mult = DEMAND_MULTIPLIER[demand_level]
    base_with_demand = base * demand_mult
    duration_discount = _duration_discount_for(duration_hours)
    final = int(round(base_with_demand * duration_discount))
    return PriceQuote(
        duration_hours=duration_hours,
        multiplier=multiplier,
        demand_level=demand_level,
        base_price_cents=int(round(base)),
        demand_multiplier_applied=demand_mult,
        duration_discount_applied=duration_discount,
        final_price_cents=final,
    )


def _duration_discount_for(hours: int) -> float:
    for upper, factor in DURATION_DISCOUNT:
        if hours <= upper:
            return factor
    return DURATION_DISCOUNT[-1][1]


def suggest_boost_price_cents(demand_level: DemandLevel) -> int:
    """
    Single-number suggestion surfaced by the Insights Engine.
    Defaults: 24h × 1.5× multiplier at the current demand.
    """
    return quote_boost_price(
        duration_hours=24,
        multiplier=1.5,
        demand_level=demand_level,
    ).final_price_cents
```

---

## 6. Ranking — `backend/domains/boosts/ranking.py`

This is the **public surface** consumed by search, matching, and the dashboard. It accepts plain inputs so callers don't need to fetch the same data twice.

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


# Weight knobs — tune empirically. Sum doesn't matter; score is relative.
W_BASE = 100.0
W_RATING = 40.0          # max boost from a perfect 5.0 rating
W_COMPLETION = 20.0      # max boost from 100% completion
W_RESPONSE = 15.0        # max boost from instant response (≤1 min)
RESPONSE_PENALTY_MIN = 30  # minutes; responses slower than this get 0

# Sentinels
NEUTRAL_RATING = 4.0     # newcomers default — same as platform median
MAX_BOOST_MULTIPLIER = 5.0  # safety cap matching DB CHECK


@dataclass(frozen=True)
class ProviderScoreInputs:
    """All ranking inputs in one place. Caller is responsible for sourcing them."""
    provider_user_id: str
    rating_avg: float | None              # 0.0–5.0 or None for newcomers
    completion_rate: float | None         # 0.0–1.0 or None
    response_time_minutes: float | None   # mean accept latency, or None
    boost_multiplier: float               # 1.0 if no active boost
    is_verified: bool = True
    is_paused: bool = False


@dataclass(frozen=True)
class ProviderScore:
    """Decomposed score so the dashboard can show 'why you rank where you do'."""
    provider_user_id: str
    final_score: float
    base_component: float
    rating_component: float
    completion_component: float
    response_component: float
    boost_multiplier: float
    boost_uplift: float                   # how many points the boost added


def compute_provider_score(inputs: ProviderScoreInputs) -> ProviderScore:
    """
    Public ranking function. Pure: every input is explicit, no side effects.

    Formula:
        merit  = W_BASE
               + W_RATING * normalize_rating(rating_avg)
               + W_COMPLETION * (completion_rate or 0)
               + W_RESPONSE * normalize_response(response_time_minutes)
        score  = merit * clamp(boost_multiplier, 1.0, MAX_BOOST_MULTIPLIER)

    Special cases:
        - paused providers always score 0 (excluded from results upstream too)
        - unverified providers also score 0
        - newcomers (no rating yet) use NEUTRAL_RATING so they aren't punished
    """
    if inputs.is_paused or not inputs.is_verified:
        return ProviderScore(
            provider_user_id=inputs.provider_user_id,
            final_score=0.0,
            base_component=0.0,
            rating_component=0.0,
            completion_component=0.0,
            response_component=0.0,
            boost_multiplier=inputs.boost_multiplier,
            boost_uplift=0.0,
        )

    rating = inputs.rating_avg if inputs.rating_avg is not None else NEUTRAL_RATING
    rating_component = W_RATING * _normalize_rating(rating)

    completion = inputs.completion_rate or 0.0
    completion_component = W_COMPLETION * max(0.0, min(1.0, completion))

    response_component = W_RESPONSE * _normalize_response(
        inputs.response_time_minutes
    )

    base = W_BASE
    merit = base + rating_component + completion_component + response_component
    boost = max(1.0, min(MAX_BOOST_MULTIPLIER, inputs.boost_multiplier))
    final = merit * boost
    uplift = final - merit

    return ProviderScore(
        provider_user_id=inputs.provider_user_id,
        final_score=final,
        base_component=base,
        rating_component=rating_component,
        completion_component=completion_component,
        response_component=response_component,
        boost_multiplier=boost,
        boost_uplift=uplift,
    )


def _normalize_rating(rating_0_to_5: float) -> float:
    """Map [3.0, 5.0] linearly to [0.0, 1.0]. Below 3.0 is 0.0."""
    if rating_0_to_5 <= 3.0:
        return 0.0
    if rating_0_to_5 >= 5.0:
        return 1.0
    return (rating_0_to_5 - 3.0) / 2.0


def _normalize_response(minutes: float | None) -> float:
    """
    Faster is better. ≤1 min → 1.0. ≥RESPONSE_PENALTY_MIN min → 0.0.
    Newcomers (None) get 0.5 — neutral.
    """
    if minutes is None:
        return 0.5
    if minutes <= 1.0:
        return 1.0
    if minutes >= RESPONSE_PENALTY_MIN:
        return 0.0
    return 1.0 - ((minutes - 1.0) / (RESPONSE_PENALTY_MIN - 1.0))
```

### 6.1 Integration into matching

In `domains/matching/service.py`, the candidate-ranking step changes from a hardcoded rating sort to:

```python
from domains.boosts.ranking import ProviderScoreInputs, compute_provider_score
from domains.boosts.repository import BoostRepository

async def rank_candidates(
    candidates: list[ProviderCandidate],
    db: AsyncSession,
) -> list[ProviderCandidate]:
    boost_repo = BoostRepository(db)
    active_boosts = await boost_repo.get_active_boosts_by_provider_ids(
        [c.provider_user_id for c in candidates]
    )
    scored: list[tuple[float, ProviderCandidate]] = []
    for c in candidates:
        boost = active_boosts.get(c.provider_user_id)
        score = compute_provider_score(ProviderScoreInputs(
            provider_user_id=str(c.provider_user_id),
            rating_avg=c.rating_avg,
            completion_rate=c.completion_rate,
            response_time_minutes=c.response_time_minutes,
            boost_multiplier=boost.multiplier if boost else 1.0,
            is_verified=c.is_verified,
            is_paused=c.is_paused,
        ))
        scored.append((score.final_score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]
```

`get_active_boosts_by_provider_ids` is a single `IN`-query — no N+1.

---

## 7. Insights Engine — `backend/domains/boosts/insights.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domains.appointments.models import Appointment, AppointmentStatus
from domains.boosts.models import DemandLevel, DemandSnapshot
from domains.boosts.pricing import suggest_boost_price_cents


# Platform-wide reference numbers — tuneable, eventually CMS-driven (plan 15).
PLATFORM_CONVERSION_RATE = 0.18         # 18 % impressions → bookings
AVG_TICKET_CENTS_FALLBACK = 12_000      # used when provider has no completed jobs
INSIGHTS_LOOKBACK_DAYS = 30


@dataclass(frozen=True)
class ProviderInsight:
    missed_earnings_cents: int
    potential_bookings: int
    recommended_action: str
    suggested_boost_price_cents: int
    demand_level: DemandLevel
    impressions_count: int
    bookings_count: int
    conversion_rate: float
    metro_slug: str
    window_start: datetime
    window_end: datetime


class InsightsEngine:
    """
    First-pass heuristic. Designed so individual signals can be swapped for
    ML scores later without changing the public response shape.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def for_provider(
        self,
        *,
        provider_user_id,
        metro_slug: str,
    ) -> ProviderInsight:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=INSIGHTS_LOOKBACK_DAYS)

        # 1. Demand for this provider's metro/category
        demand = await self._latest_demand(metro_slug)
        demand_level = DemandLevel(demand.demand_level) if demand else DemandLevel.MEDIUM
        market_cvr = demand.conversion_rate if demand else PLATFORM_CONVERSION_RATE
        impressions = demand.impressions_count if demand else 0

        # 2. Provider's own bookings + avg ticket
        bookings_count, avg_ticket_cents = await self._provider_stats(
            provider_user_id, window_start, now
        )

        # 3. Missed earnings = (expected conversion × impressions − actual bookings)
        #    × avg ticket. Clamped to ≥0 so a provider above market doesn't
        #    get a "you're missing money" insight.
        expected_bookings = int(impressions * market_cvr)
        missed_bookings = max(0, expected_bookings - bookings_count)
        ticket = avg_ticket_cents or AVG_TICKET_CENTS_FALLBACK
        missed_earnings = missed_bookings * ticket

        # 4. Recommendation
        action = self._recommend(
            demand_level=demand_level,
            missed_bookings=missed_bookings,
            bookings_count=bookings_count,
        )
        suggested = suggest_boost_price_cents(demand_level)

        return ProviderInsight(
            missed_earnings_cents=missed_earnings,
            potential_bookings=missed_bookings,
            recommended_action=action,
            suggested_boost_price_cents=suggested,
            demand_level=demand_level,
            impressions_count=impressions,
            bookings_count=bookings_count,
            conversion_rate=market_cvr,
            metro_slug=metro_slug,
            window_start=window_start,
            window_end=now,
        )

    async def _latest_demand(self, metro_slug: str) -> DemandSnapshot | None:
        stmt = (
            select(DemandSnapshot)
            .where(DemandSnapshot.metro_slug == metro_slug)
            .order_by(DemandSnapshot.window_start.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _provider_stats(
        self,
        provider_user_id,
        start: datetime,
        end: datetime,
    ) -> tuple[int, int]:
        stmt = (
            select(
                func.count(Appointment.id),
                func.coalesce(
                    func.avg(Appointment.actual_price_cents), 0
                ).cast(func.Integer),
            )
            .where(
                Appointment.detailer_user_id == provider_user_id,
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.completed_at >= start,
                Appointment.completed_at <= end,
                Appointment.is_deleted.is_(False),
            )
        )
        row = (await self.db.execute(stmt)).one()
        return int(row[0] or 0), int(row[1] or 0)

    @staticmethod
    def _recommend(
        *,
        demand_level: DemandLevel,
        missed_bookings: int,
        bookings_count: int,
    ) -> str:
        if demand_level == DemandLevel.HIGH and missed_bookings >= 3:
            return (
                "Demand is high in your area and you're missing "
                f"~{missed_bookings} bookings. A 24-hour boost would "
                "lift you above your competition while it's hot."
            )
        if demand_level == DemandLevel.HIGH:
            return (
                "Demand is high and you're keeping pace. A short boost "
                "could push you into the top tier of your local market."
            )
        if bookings_count == 0:
            return (
                "You haven't completed any jobs in the last 30 days. A "
                "boost can put you in front of new clients fast."
            )
        if missed_bookings >= 5:
            return (
                f"Your impressions outpace your bookings by ~{missed_bookings} "
                "jobs. Featuring your top service may convert more views."
            )
        return (
            "You're tracking with the market. Boosts are best timed during "
            "high-demand windows — check back when demand turns red."
        )
```

---

## 8. Payment gateway abstraction — `backend/domains/boosts/payment_gateway.py`

```python
from __future__ import annotations

import abc
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class ChargeResult:
    success: bool
    gateway_intent_id: str
    gateway_charge_id: str | None
    failure_reason: str | None
    raw_response: dict


@dataclass(frozen=True)
class RefundResult:
    success: bool
    refund_id: str
    failure_reason: str | None


class PaymentGateway(abc.ABC):
    """
    Abstract interface. The simulated impl lets us ship the full
    purchase flow + ledger reconciliation without waiting on Stripe.
    Swapping in `StripeGateway` only changes the wiring in this domain.
    """
    name: str

    @abc.abstractmethod
    async def charge(
        self,
        *,
        amount_cents: int,
        currency: str,
        customer_user_id,
        idempotency_key: str,
        description: str,
        metadata: dict,
    ) -> ChargeResult: ...

    @abc.abstractmethod
    async def refund(
        self,
        *,
        gateway_charge_id: str,
        amount_cents: int,
        reason: str,
    ) -> RefundResult: ...


class SimulatedGateway(PaymentGateway):
    """
    Always-succeeds in-memory implementation. Returns deterministic IDs
    derived from idempotency_key so retried requests reconcile cleanly.
    """
    name = "simulated"

    async def charge(
        self,
        *,
        amount_cents: int,
        currency: str,
        customer_user_id,
        idempotency_key: str,
        description: str,
        metadata: dict,
    ) -> ChargeResult:
        intent_id = f"sim_intent_{idempotency_key[:24]}"
        charge_id = f"sim_charge_{idempotency_key[:24]}"
        return ChargeResult(
            success=True,
            gateway_intent_id=intent_id,
            gateway_charge_id=charge_id,
            failure_reason=None,
            raw_response={
                "amount_cents": amount_cents,
                "currency": currency,
                "description": description,
                "metadata": metadata,
            },
        )

    async def refund(
        self,
        *,
        gateway_charge_id: str,
        amount_cents: int,
        reason: str,
    ) -> RefundResult:
        return RefundResult(
            success=True,
            refund_id=f"sim_refund_{secrets.token_hex(8)}",
            failure_reason=None,
        )


def get_payment_gateway() -> PaymentGateway:
    """
    Dependency-injectable factory. Today returns SimulatedGateway;
    swap for StripeGateway once Stripe Connect is wired (plan 11 Phase 4).
    """
    return SimulatedGateway()
```

---

## 9. Repository — `backend/domains/boosts/repository.py`

All DB I/O lives here. Service layer holds zero SQL.

```python
from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domains.boosts.models import (
    BoostInvoice, BoostStatus, BoostType, FeaturedService, ProviderBoost,
)


class BoostRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── ProviderBoost ──────────────────────────────────────────────────

    async def get_active_boost(
        self,
        provider_user_id: uuid.UUID,
        boost_type: BoostType = BoostType.SEARCH_BOOST,
    ) -> ProviderBoost | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(ProviderBoost)
            .where(
                ProviderBoost.provider_user_id == provider_user_id,
                ProviderBoost.type == boost_type.value,
                ProviderBoost.status == BoostStatus.ACTIVE.value,
                ProviderBoost.expires_at > now,
            )
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_active_boosts_by_provider_ids(
        self,
        provider_user_ids: Iterable[uuid.UUID],
    ) -> dict[uuid.UUID, ProviderBoost]:
        """Single IN-query — keeps ranking O(1) DB hits regardless of candidate count."""
        ids = list(provider_user_ids)
        if not ids:
            return {}
        now = datetime.now(timezone.utc)
        stmt = (
            select(ProviderBoost)
            .where(
                ProviderBoost.provider_user_id.in_(ids),
                ProviderBoost.status == BoostStatus.ACTIVE.value,
                ProviderBoost.expires_at > now,
            )
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return {b.provider_user_id: b for b in rows}

    async def create_boost(self, boost: ProviderBoost) -> ProviderBoost:
        self.db.add(boost)
        await self.db.flush()
        return boost

    async def activate(self, boost_id: uuid.UUID) -> None:
        stmt = (
            update(ProviderBoost)
            .where(ProviderBoost.id == boost_id)
            .values(status=BoostStatus.ACTIVE.value)
        )
        await self.db.execute(stmt)

    async def cancel(self, boost_id: uuid.UUID) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(ProviderBoost)
            .where(ProviderBoost.id == boost_id)
            .values(status=BoostStatus.CANCELLED.value, cancelled_at=now)
        )
        await self.db.execute(stmt)

    async def expire_due(self, *, batch_size: int = 500) -> list[uuid.UUID]:
        """
        Mark every active boost whose expires_at has passed as `expired`.
        Returns the IDs touched so callers can audit + emit events.
        """
        now = datetime.now(timezone.utc)
        # Find first to log IDs; UPDATE...RETURNING would be nicer in Postgres.
        stmt = (
            select(ProviderBoost.id)
            .where(
                ProviderBoost.status == BoostStatus.ACTIVE.value,
                ProviderBoost.expires_at <= now,
            )
            .limit(batch_size)
        )
        ids = [r[0] for r in (await self.db.execute(stmt)).all()]
        if not ids:
            return []
        await self.db.execute(
            update(ProviderBoost)
            .where(ProviderBoost.id.in_(ids))
            .values(status=BoostStatus.EXPIRED.value)
        )
        return ids

    # ─── FeaturedService ────────────────────────────────────────────────

    async def list_active_featured(
        self, provider_user_id: uuid.UUID,
    ) -> list[FeaturedService]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(FeaturedService)
            .where(
                FeaturedService.provider_user_id == provider_user_id,
                FeaturedService.expires_at > now,
            )
            .order_by(FeaturedService.expires_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_active_featured(
        self,
        provider_user_id: uuid.UUID,
        service_id: uuid.UUID,
    ) -> FeaturedService | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(FeaturedService)
            .where(
                FeaturedService.provider_user_id == provider_user_id,
                FeaturedService.service_id == service_id,
                FeaturedService.expires_at > now,
            )
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_featured(self, featured: FeaturedService) -> FeaturedService:
        self.db.add(featured)
        await self.db.flush()
        return featured

    # ─── BoostInvoice ───────────────────────────────────────────────────

    async def get_invoice_by_idempotency(
        self,
        provider_user_id: uuid.UUID,
        idempotency_key: str,
    ) -> BoostInvoice | None:
        stmt = (
            select(BoostInvoice)
            .where(
                BoostInvoice.provider_user_id == provider_user_id,
                BoostInvoice.idempotency_key == idempotency_key,
            )
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create_invoice(self, inv: BoostInvoice) -> BoostInvoice:
        self.db.add(inv)
        await self.db.flush()
        return inv

    async def mark_invoice_paid(
        self,
        invoice_id: uuid.UUID,
        *,
        gateway_intent_id: str,
        gateway_charge_id: str | None,
    ) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(BoostInvoice)
            .where(BoostInvoice.id == invoice_id)
            .values(
                status="succeeded",
                gateway_intent_id=gateway_intent_id,
                gateway_charge_id=gateway_charge_id,
                succeeded_at=now,
            )
        )
        await self.db.execute(stmt)

    async def mark_invoice_failed(
        self,
        invoice_id: uuid.UUID,
        *,
        failure_reason: str,
    ) -> None:
        stmt = (
            update(BoostInvoice)
            .where(BoostInvoice.id == invoice_id)
            .values(status="failed", failure_reason=failure_reason)
        )
        await self.db.execute(stmt)
```

---

## 10. Service layer — `backend/domains/boosts/service.py`

The service is the only place that knows about cross-domain rules: payment gateway, audit logging, FSM transitions, idempotency. Routes call services; services orchestrate repositories.

```python
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from domains.audit.models import AuditAction
from domains.audit.repository import AuditRepository
from domains.boosts.insights import InsightsEngine
from domains.boosts.models import (
    BoostInvoice, BoostStatus, BoostType, FeaturedService, ProviderBoost,
)
from domains.boosts.payment_gateway import PaymentGateway
from domains.boosts.pricing import (
    ALLOWED_MULTIPLIERS, MAX_DURATION_HOURS, MIN_DURATION_HOURS, quote_boost_price,
)
from domains.boosts.repository import BoostRepository

logger = logging.getLogger(__name__)


FEATURED_SERVICE_DEFAULT_DURATION_HOURS = 168  # 7 days
FEATURED_SERVICE_PRICE_CENTS = 1_999          # $19.99 flat


class BoostService:
    def __init__(
        self,
        db: AsyncSession,
        repo: BoostRepository,
        audit: AuditRepository,
        gateway: PaymentGateway,
        insights: InsightsEngine,
    ):
        self.db = db
        self.repo = repo
        self.audit = audit
        self.gateway = gateway
        self.insights = insights

    # ─── Boost purchase ─────────────────────────────────────────────────

    async def purchase_boost(
        self,
        *,
        provider_user_id: uuid.UUID,
        duration_hours: int,
        multiplier: float,
        metro_slug: str,
        idempotency_key: str,
        actor_id: uuid.UUID,
        request_id: str | None,
    ) -> tuple[ProviderBoost, BoostInvoice]:
        # 1. Idempotency: same key → same boost (no double-charge).
        existing_invoice = await self.repo.get_invoice_by_idempotency(
            provider_user_id, idempotency_key
        )
        if existing_invoice is not None:
            boost = await self._boost_for_invoice(existing_invoice.id)
            if boost is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency_key reused for a different operation",
                )
            return boost, existing_invoice

        # 2. Reject if an active boost already exists for this type.
        active = await self.repo.get_active_boost(
            provider_user_id, BoostType.SEARCH_BOOST,
        )
        if active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "boost_already_active",
                    "message": "An active boost already exists for this provider.",
                    "active_boost_id": str(active.id),
                    "expires_at": active.expires_at.isoformat(),
                },
            )

        # 3. Validate inputs.
        if duration_hours < MIN_DURATION_HOURS or duration_hours > MAX_DURATION_HOURS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"duration_hours must be in [{MIN_DURATION_HOURS}, {MAX_DURATION_HOURS}]",
            )
        if multiplier not in ALLOWED_MULTIPLIERS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"multiplier must be one of {ALLOWED_MULTIPLIERS}",
            )

        # 4. Compute price using current demand.
        insight = await self.insights.for_provider(
            provider_user_id=provider_user_id,
            metro_slug=metro_slug,
        )
        quote = quote_boost_price(
            duration_hours=duration_hours,
            multiplier=multiplier,
            demand_level=insight.demand_level,
        )

        # 5. Create invoice (pending) — gives us an idempotency anchor before charge.
        invoice = BoostInvoice(
            id=uuid.uuid4(),
            provider_user_id=provider_user_id,
            kind="boost",
            amount_cents=quote.final_price_cents,
            currency="USD",
            status="pending",
            payment_gateway=self.gateway.name,
            idempotency_key=idempotency_key,
            metadata_json={
                "duration_hours": duration_hours,
                "multiplier": multiplier,
                "demand_level": insight.demand_level.value,
                "request_id": request_id,
            },
        )
        await self.repo.create_invoice(invoice)

        # 6. Charge.
        charge = await self.gateway.charge(
            amount_cents=quote.final_price_cents,
            currency="USD",
            customer_user_id=provider_user_id,
            idempotency_key=idempotency_key,
            description=f"Search boost · {duration_hours}h × {multiplier}",
            metadata={
                "invoice_id": str(invoice.id),
                "provider_user_id": str(provider_user_id),
            },
        )
        if not charge.success:
            await self.repo.mark_invoice_failed(
                invoice.id,
                failure_reason=charge.failure_reason or "gateway_declined",
            )
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "payment_failed",
                    "message": charge.failure_reason or "Payment declined.",
                },
            )
        await self.repo.mark_invoice_paid(
            invoice.id,
            gateway_intent_id=charge.gateway_intent_id,
            gateway_charge_id=charge.gateway_charge_id,
        )

        # 7. Create the boost (active immediately).
        now = datetime.now(timezone.utc)
        boost = ProviderBoost(
            id=uuid.uuid4(),
            provider_user_id=provider_user_id,
            type=BoostType.SEARCH_BOOST.value,
            multiplier=multiplier,
            starts_at=now,
            expires_at=now + timedelta(hours=duration_hours),
            status=BoostStatus.ACTIVE.value,
            price_cents=quote.final_price_cents,
            base_price_cents=quote.base_price_cents,
            demand_multiplier_applied=quote.demand_multiplier_applied,
            demand_level_at_purchase=insight.demand_level.value,
            invoice_id=invoice.id,
            metadata_json={"request_id": request_id, "metro_slug": metro_slug},
        )
        try:
            await self.repo.create_boost(boost)
        except Exception:
            # Race: another concurrent purchase activated a boost between
            # our check and insert. The partial unique index will reject us.
            # Refund and surface a clean 409 so the client can retry once
            # the existing boost expires.
            await self.gateway.refund(
                gateway_charge_id=charge.gateway_charge_id or charge.gateway_intent_id,
                amount_cents=quote.final_price_cents,
                reason="duplicate_active_boost_race",
            )
            await self.repo.mark_invoice_paid  # status already succeeded; flip to refunded
            invoice.status = "refunded"
            invoice.refunded_at = datetime.now(timezone.utc)
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "boost_already_active",
                    "message": "An active boost was created by a concurrent request.",
                },
            )

        # 8. Audit + commit.
        await self.audit.record(
            actor_id=actor_id,
            action=AuditAction.PROVIDER_BOOST_PURCHASED,
            entity_type="provider_boost",
            entity_id=boost.id,
            metadata={
                "invoice_id": str(invoice.id),
                "amount_cents": quote.final_price_cents,
                "duration_hours": duration_hours,
                "multiplier": multiplier,
                "demand_level": insight.demand_level.value,
            },
        )
        await self.db.commit()
        return boost, invoice

    async def get_active_boost(
        self, provider_user_id: uuid.UUID,
    ) -> ProviderBoost | None:
        return await self.repo.get_active_boost(provider_user_id)

    async def cancel_boost(
        self,
        *,
        provider_user_id: uuid.UUID,
        boost_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        boost = await self.repo.get_active_boost(provider_user_id)
        if not boost or boost.id != boost_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active boost matching that id for this provider.",
            )
        await self.repo.cancel(boost_id)
        await self.audit.record(
            actor_id=actor_id,
            action=AuditAction.PROVIDER_BOOST_CANCELLED,
            entity_type="provider_boost",
            entity_id=boost_id,
            metadata={},
        )
        await self.db.commit()

    # ─── Featured services ──────────────────────────────────────────────

    async def feature_service(
        self,
        *,
        provider_user_id: uuid.UUID,
        service_id: uuid.UUID,
        idempotency_key: str,
        actor_id: uuid.UUID,
        duration_hours: int = FEATURED_SERVICE_DEFAULT_DURATION_HOURS,
    ) -> tuple[FeaturedService, BoostInvoice]:
        existing = await self.repo.get_active_featured(provider_user_id, service_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "service_already_featured",
                    "message": "That service is already featured.",
                    "expires_at": existing.expires_at.isoformat(),
                },
            )

        invoice = BoostInvoice(
            id=uuid.uuid4(),
            provider_user_id=provider_user_id,
            kind="featured",
            amount_cents=FEATURED_SERVICE_PRICE_CENTS,
            currency="USD",
            status="pending",
            payment_gateway=self.gateway.name,
            idempotency_key=idempotency_key,
            metadata_json={"service_id": str(service_id), "duration_hours": duration_hours},
        )
        await self.repo.create_invoice(invoice)

        charge = await self.gateway.charge(
            amount_cents=FEATURED_SERVICE_PRICE_CENTS,
            currency="USD",
            customer_user_id=provider_user_id,
            idempotency_key=idempotency_key,
            description=f"Featured service · {duration_hours}h",
            metadata={"invoice_id": str(invoice.id), "service_id": str(service_id)},
        )
        if not charge.success:
            await self.repo.mark_invoice_failed(invoice.id, failure_reason=charge.failure_reason or "")
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={"code": "payment_failed", "message": charge.failure_reason or "Declined."},
            )
        await self.repo.mark_invoice_paid(
            invoice.id,
            gateway_intent_id=charge.gateway_intent_id,
            gateway_charge_id=charge.gateway_charge_id,
        )

        now = datetime.now(timezone.utc)
        featured = FeaturedService(
            id=uuid.uuid4(),
            provider_user_id=provider_user_id,
            service_id=service_id,
            starts_at=now,
            expires_at=now + timedelta(hours=duration_hours),
            price_cents=FEATURED_SERVICE_PRICE_CENTS,
            invoice_id=invoice.id,
        )
        await self.repo.create_featured(featured)
        await self.audit.record(
            actor_id=actor_id,
            action=AuditAction.PROVIDER_FEATURED_SERVICE_PURCHASED,
            entity_type="featured_service",
            entity_id=featured.id,
            metadata={"service_id": str(service_id), "amount_cents": FEATURED_SERVICE_PRICE_CENTS},
        )
        await self.db.commit()
        return featured, invoice

    async def list_featured(
        self, provider_user_id: uuid.UUID,
    ) -> list[FeaturedService]:
        return await self.repo.list_active_featured(provider_user_id)

    # ─── Expiration sweep (called from background worker) ───────────────

    async def expire_due(self, *, batch_size: int = 500) -> int:
        ids = await self.repo.expire_due(batch_size=batch_size)
        if ids:
            logger.info("expired_boosts", extra={"count": len(ids)})
        await self.db.commit()
        return len(ids)

    async def _boost_for_invoice(self, invoice_id: uuid.UUID) -> ProviderBoost | None:
        from sqlalchemy import select
        stmt = (
            select(ProviderBoost)
            .where(ProviderBoost.invoice_id == invoice_id)
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()
```

Two new audit actions need to be added to `domains/audit/models.py::AuditAction`:
- `PROVIDER_BOOST_PURCHASED = "provider_boost_purchased"`
- `PROVIDER_BOOST_CANCELLED = "provider_boost_cancelled"`
- `PROVIDER_FEATURED_SERVICE_PURCHASED = "provider_featured_service_purchased"`

---

## 11. Pydantic schemas — `backend/domains/boosts/schemas.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field, field_validator

from domains.boosts.models import BoostStatus, BoostType, DemandLevel
from domains.boosts.pricing import ALLOWED_MULTIPLIERS, MAX_DURATION_HOURS, MIN_DURATION_HOURS
from shared.schemas import _BaseRequestSchema, _BaseSchema


# ─── Requests ───────────────────────────────────────────────────────────

class BoostPurchaseRequest(_BaseRequestSchema):
    duration_hours: int = Field(..., ge=MIN_DURATION_HOURS, le=MAX_DURATION_HOURS)
    multiplier: float = Field(..., examples=[1.2, 1.5, 2.0])
    metro_slug: str = Field(..., min_length=2, max_length=64)

    @field_validator("multiplier")
    @classmethod
    def _multiplier_allowed(cls, v: float) -> float:
        if v not in ALLOWED_MULTIPLIERS:
            raise ValueError(f"multiplier must be one of {ALLOWED_MULTIPLIERS}")
        return v


class FeaturedServiceRequest(_BaseRequestSchema):
    service_id: uuid.UUID
    duration_hours: int = Field(168, ge=24, le=720)  # 1 day – 30 days


# ─── Responses ──────────────────────────────────────────────────────────

class BoostInvoiceRead(_BaseSchema):
    id: uuid.UUID
    kind: str
    amount_cents: int
    currency: str
    status: str
    payment_gateway: str
    gateway_intent_id: str | None
    gateway_charge_id: str | None
    succeeded_at: datetime | None


class ProviderBoostRead(_BaseSchema):
    id: uuid.UUID
    provider_user_id: uuid.UUID
    type: BoostType
    multiplier: float
    starts_at: datetime
    expires_at: datetime
    status: BoostStatus
    price_cents: int
    base_price_cents: int
    demand_multiplier_applied: float
    demand_level_at_purchase: DemandLevel
    invoice: BoostInvoiceRead | None
    created_at: datetime


class BoostPurchaseResponse(_BaseSchema):
    boost: ProviderBoostRead
    invoice: BoostInvoiceRead
    price_charged_cents: int


class FeaturedServiceRead(_BaseSchema):
    id: uuid.UUID
    provider_user_id: uuid.UUID
    service_id: uuid.UUID
    starts_at: datetime
    expires_at: datetime
    price_cents: int
    invoice: BoostInvoiceRead | None
    created_at: datetime


class InsightResponse(_BaseSchema):
    missed_earnings_cents: int
    potential_bookings: int
    recommended_action: str
    suggested_boost_price_cents: int
    demand_level: DemandLevel
    impressions_count: int
    bookings_count: int
    conversion_rate: float
    metro_slug: str
    window_start: datetime
    window_end: datetime
```

---

## 12. Routes — `backend/domains/boosts/router.py`

```python
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from domains.audit.repository import AuditRepository
from domains.auth.service import get_current_user, require_role
from domains.boosts.insights import InsightsEngine
from domains.boosts.payment_gateway import PaymentGateway, get_payment_gateway
from domains.boosts.repository import BoostRepository
from domains.boosts.schemas import (
    BoostPurchaseRequest, BoostPurchaseResponse, FeaturedServiceRead,
    FeaturedServiceRequest, InsightResponse, ProviderBoostRead,
)
from domains.boosts.service import BoostService
from domains.users.models import User
from infrastructure.db.session import get_db
from shared.schemas import Envelope


router = APIRouter(prefix="/api/v1/provider", tags=["Provider · Boosts"])


def _service(
    db: AsyncSession = Depends(get_db),
    gateway: PaymentGateway = Depends(get_payment_gateway),
) -> BoostService:
    return BoostService(
        db=db,
        repo=BoostRepository(db),
        audit=AuditRepository(db),
        gateway=gateway,
        insights=InsightsEngine(db),
    )


def _provider_metro(user: User) -> str:
    """
    Resolve the provider's primary metro slug. Today it lives on the
    user's primary address; later it'll move to `provider_profiles.metro_id`.
    Falls back to "fort-wayne-in" so the system never 500s on missing data.
    """
    metro = getattr(getattr(user, "primary_address", None), "metro_slug", None)
    return metro or "fort-wayne-in"


# ─── Boosts ──────────────────────────────────────────────────────────────

@router.post(
    "/boosts",
    response_model=Envelope[BoostPurchaseResponse],
    status_code=status.HTTP_201_CREATED,
)
async def purchase_boost(
    payload: BoostPurchaseRequest,
    request: Request,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=64),
    current_user: User = Depends(require_role("detailer")),
    service: BoostService = Depends(_service),
) -> Envelope[BoostPurchaseResponse]:
    boost, invoice = await service.purchase_boost(
        provider_user_id=current_user.id,
        duration_hours=payload.duration_hours,
        multiplier=payload.multiplier,
        metro_slug=payload.metro_slug,
        idempotency_key=idempotency_key,
        actor_id=current_user.id,
        request_id=getattr(request.state, "request_id", None),
    )
    return Envelope(
        data=BoostPurchaseResponse(
            boost=ProviderBoostRead.model_validate(boost),
            invoice=invoice,
            price_charged_cents=invoice.amount_cents,
        )
    )


@router.get(
    "/boosts/active",
    response_model=Envelope[ProviderBoostRead | None],
)
async def get_active_boost(
    current_user: User = Depends(require_role("detailer")),
    service: BoostService = Depends(_service),
) -> Envelope[ProviderBoostRead | None]:
    boost = await service.get_active_boost(current_user.id)
    return Envelope(data=ProviderBoostRead.model_validate(boost) if boost else None)


@router.delete(
    "/boosts/{boost_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_boost(
    boost_id: uuid.UUID,
    current_user: User = Depends(require_role("detailer")),
    service: BoostService = Depends(_service),
) -> None:
    await service.cancel_boost(
        provider_user_id=current_user.id,
        boost_id=boost_id,
        actor_id=current_user.id,
    )


# ─── Insights ────────────────────────────────────────────────────────────

@router.get(
    "/insights",
    response_model=Envelope[InsightResponse],
)
async def get_insights(
    current_user: User = Depends(require_role("detailer")),
    service: BoostService = Depends(_service),
) -> Envelope[InsightResponse]:
    insight = await service.insights.for_provider(
        provider_user_id=current_user.id,
        metro_slug=_provider_metro(current_user),
    )
    return Envelope(data=InsightResponse.model_validate(insight, from_attributes=True))


# ─── Featured services ───────────────────────────────────────────────────

@router.post(
    "/featured-services",
    response_model=Envelope[FeaturedServiceRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_featured_service(
    payload: FeaturedServiceRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=64),
    current_user: User = Depends(require_role("detailer")),
    service: BoostService = Depends(_service),
) -> Envelope[FeaturedServiceRead]:
    featured, _ = await service.feature_service(
        provider_user_id=current_user.id,
        service_id=payload.service_id,
        idempotency_key=idempotency_key,
        actor_id=current_user.id,
        duration_hours=payload.duration_hours,
    )
    return Envelope(data=FeaturedServiceRead.model_validate(featured))


@router.get(
    "/featured-services",
    response_model=Envelope[list[FeaturedServiceRead]],
)
async def list_featured_services(
    current_user: User = Depends(require_role("detailer")),
    service: BoostService = Depends(_service),
) -> Envelope[list[FeaturedServiceRead]]:
    items = await service.list_featured(current_user.id)
    return Envelope(data=[FeaturedServiceRead.model_validate(i) for i in items])
```

Mount in `api/router.py`:

```python
from domains.boosts.router import router as boosts_router
api_router.include_router(boosts_router)
```

---

## 13. Background worker — `backend/domains/boosts/tasks.py`

```python
from __future__ import annotations

import asyncio
import logging

from infrastructure.db.session import async_session_factory
from domains.audit.repository import AuditRepository
from domains.boosts.insights import InsightsEngine
from domains.boosts.payment_gateway import get_payment_gateway
from domains.boosts.repository import BoostRepository
from domains.boosts.service import BoostService


logger = logging.getLogger(__name__)

EXPIRATION_SWEEP_INTERVAL_SECONDS = 60


async def expire_boosts_sweep() -> None:
    """
    Runs every minute. The DB-level safety net is already in place (queries
    filter on `status='active' AND expires_at>NOW()`), so this worker exists
    only to flip rows to `expired` for clean reporting and to free up the
    partial-unique-index slot so providers can immediately buy a new boost
    once their old one ages out.
    """
    async with async_session_factory() as db:
        service = BoostService(
            db=db,
            repo=BoostRepository(db),
            audit=AuditRepository(db),
            gateway=get_payment_gateway(),
            insights=InsightsEngine(db),
        )
        try:
            n = await service.expire_due()
            if n:
                logger.info("boost_expiration_sweep", extra={"expired": n})
        except Exception as exc:
            logger.exception("boost_expiration_sweep_failed", extra={"error": str(exc)})
            await db.rollback()


async def expire_boosts_loop() -> None:
    while True:
        await expire_boosts_sweep()
        await asyncio.sleep(EXPIRATION_SWEEP_INTERVAL_SECONDS)
```

Registered in the existing `workers/__init__.py` orchestrator alongside the location-update and assignment workers.

> **Belt-and-suspenders**: the worker is a convenience. Even if it never runs, ranking queries filter on `status='active' AND expires_at>NOW()`, so an expired boost never affects results. The worker just keeps the table tidy.

---

## 14. Search integration — example call site

```python
# domains/matching/service.py (excerpt)
from domains.boosts.ranking import ProviderScoreInputs, compute_provider_score
from domains.boosts.repository import BoostRepository

async def find_top_providers(
    *,
    zip_code: str,
    service_id: uuid.UUID,
    limit: int,
    db: AsyncSession,
) -> list[ProviderCandidate]:
    candidates = await _candidate_pool(zip_code, service_id, db)
    if not candidates:
        return []

    boosts = await BoostRepository(db).get_active_boosts_by_provider_ids(
        [c.provider_user_id for c in candidates]
    )

    scored = [
        (
            compute_provider_score(ProviderScoreInputs(
                provider_user_id=str(c.provider_user_id),
                rating_avg=c.rating_avg,
                completion_rate=c.completion_rate,
                response_time_minutes=c.response_time_minutes,
                boost_multiplier=boosts.get(c.provider_user_id, _NO_BOOST).multiplier
                if c.provider_user_id in boosts else 1.0,
                is_verified=c.is_verified,
                is_paused=c.is_paused,
            )),
            c,
        )
        for c in candidates
    ]
    scored.sort(key=lambda x: x[0].final_score, reverse=True)
    return [c for _, c in scored[:limit]]
```

---

## 15. Example JSON responses

### 15.1 `POST /api/v1/provider/boosts`

Request:
```http
POST /api/v1/provider/boosts
Authorization: Bearer <provider_jwt>
Idempotency-Key: 7c6f9c1e-bb1c-4d3d-9b2c-92a55cb8e2c1
Content-Type: application/json

{
  "duration_hours": 24,
  "multiplier": 1.5,
  "metro_slug": "fort-wayne-in"
}
```

Response `201 Created`:
```json
{
  "data": {
    "boost": {
      "id": "5f1d2a3b-4c5e-4f6a-8b7c-9d0e1f2a3b4c",
      "provider_user_id": "11111111-2222-3333-4444-555555555555",
      "type": "search_boost",
      "multiplier": 1.5,
      "starts_at": "2026-05-19T15:42:00Z",
      "expires_at": "2026-05-20T15:42:00Z",
      "status": "active",
      "price_cents": 3279,
      "base_price_cents": 3564,
      "demand_multiplier_applied": 1.0,
      "demand_level_at_purchase": "medium",
      "invoice": {
        "id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
        "kind": "boost",
        "amount_cents": 3279,
        "currency": "USD",
        "status": "succeeded",
        "payment_gateway": "simulated",
        "gateway_intent_id": "sim_intent_7c6f9c1ebb1c4d3d9b2c",
        "gateway_charge_id": "sim_charge_7c6f9c1ebb1c4d3d9b2c",
        "succeeded_at": "2026-05-19T15:42:00Z"
      },
      "created_at": "2026-05-19T15:42:00Z"
    },
    "invoice": { "...": "same as above" },
    "price_charged_cents": 3279
  }
}
```

### 15.2 `GET /api/v1/provider/boosts/active`

```json
{
  "data": {
    "id": "5f1d2a3b-4c5e-4f6a-8b7c-9d0e1f2a3b4c",
    "type": "search_boost",
    "multiplier": 1.5,
    "starts_at": "2026-05-19T15:42:00Z",
    "expires_at": "2026-05-20T15:42:00Z",
    "status": "active",
    "price_cents": 3279,
    "demand_level_at_purchase": "medium",
    "created_at": "2026-05-19T15:42:00Z"
  }
}
```

When no active boost exists: `{ "data": null }`.

### 15.3 `GET /api/v1/provider/insights`

```json
{
  "data": {
    "missed_earnings_cents": 48000,
    "potential_bookings": 4,
    "recommended_action": "Demand is high in your area and you're missing ~4 bookings. A 24-hour boost would lift you above your competition while it's hot.",
    "suggested_boost_price_cents": 4458,
    "demand_level": "high",
    "impressions_count": 312,
    "bookings_count": 52,
    "conversion_rate": 0.18,
    "metro_slug": "fort-wayne-in",
    "window_start": "2026-04-19T15:42:00Z",
    "window_end": "2026-05-19T15:42:00Z"
  }
}
```

### 15.4 `POST /api/v1/provider/featured-services`

```json
{
  "data": {
    "id": "8c1d2e3f-4a5b-4c6d-9e7f-0a1b2c3d4e5f",
    "provider_user_id": "11111111-2222-3333-4444-555555555555",
    "service_id": "aaaa1111-bbbb-2222-cccc-333333333333",
    "starts_at": "2026-05-19T15:50:00Z",
    "expires_at": "2026-05-26T15:50:00Z",
    "price_cents": 1999,
    "invoice": {
      "id": "...",
      "kind": "featured",
      "amount_cents": 1999,
      "status": "succeeded",
      "payment_gateway": "simulated",
      "succeeded_at": "2026-05-19T15:50:00Z"
    },
    "created_at": "2026-05-19T15:50:00Z"
  }
}
```

### 15.5 Error: active boost already exists

```http
HTTP/1.1 409 Conflict
```
```json
{
  "error": {
    "code": "boost_already_active",
    "message": "An active boost already exists for this provider.",
    "details": null,
    "request_id": "req_8f3a2c1b"
  },
  "meta": null
}
```

---

## 16. Testing strategy

### 16.1 Unit tests (no DB)
- `pricing.quote_boost_price` — boundary durations, all multipliers, all demand levels, rounding correctness.
- `ranking.compute_provider_score` — newcomer (None rating), paused, unverified, max multiplier cap, response normalization edges.
- `insights.InsightsEngine._recommend` — every branch of the heuristic.

### 16.2 Integration tests (`backend/tests/test_boosts.py`)
- `test_purchase_boost_happy_path`: provider with no active boost → 201 + boost active + ledger correct.
- `test_purchase_boost_duplicate_idempotency_key`: same key twice → same boost, only one invoice.
- `test_purchase_boost_active_already_exists`: 409 conflict, no charge.
- `test_purchase_boost_payment_failure`: gateway returns failed → 402, invoice marked failed, no boost row.
- `test_concurrent_purchase_race_yields_one_boost`: two concurrent requests with different idempotency keys → exactly one boost, the loser is refunded.
- `test_expire_due_marks_boosts_expired`: insert active boost with expires_at in the past, run sweep, assert status flipped.
- `test_ranking_uses_active_boost_only`: provider with active + expired + cancelled boosts → score uses only active.
- `test_role_guard_rejects_client`: client JWT hitting any endpoint → 403.
- `test_feature_service_uniqueness`: 409 on second feature of same (provider, service) while active.
- `test_get_insights_returns_expected_shape`: with seeded demand snapshot + appointments.

### 16.3 Performance test
- Generate 10,000 providers, 1,000 with active boosts. Run `find_top_providers` 100 times. Assert P95 < 80 ms.

---

## 17. Execution phases

| Phase | Scope | Weeks |
|---|---|---|
| 1 | Models + migration + repository + pricing + ranking unit tests | 1 |
| 2 | Service + simulated gateway + audit + idempotency | 1 |
| 3 | Routes + schemas + integration tests | 1 |
| 4 | Insights engine + demand snapshot worker | 1 |
| 5 | Provider Dashboard "Boosts & Visibility" tab (plan 11) | 1 |
| 6 | Stripe gateway swap (after plan 11 Phase 4 ships Connect onboarding) | 1 |
| 7 | Featured-service surfacing in client booking flow | 1 |

---

## 18. Risks

| Risk | Mitigation |
|---|---|
| Provider double-charged on retry | Idempotency-Key required on every POST; partial unique on invoices `(provider, key)` enforces it at DB level. |
| Two providers race to buy a boost at the same instant | Partial unique index `uq_provider_boosts_active_per_type` rejects the second insert; service refunds the loser. |
| Expired boost still affects ranking | Ranking queries filter `status='active' AND expires_at>NOW()`; worker is belt-and-suspenders only. |
| Insights heuristic is wrong / users distrust it | Show the input numbers (impressions / bookings / cvr) alongside the recommendation so providers can sanity-check. |
| Demand snapshot worker stalls | Pricing falls back to `DemandLevel.MEDIUM`; surfaced as an alert in observability (plan 07). |
| Boost CPI is too low → unprofitable | Pricing constants live in `pricing.py` as named constants; admin-tunable in plan 15 later. |
| Refund flow leaves boost active | Service is transactional; `db.commit()` only after both invoice + boost succeed. Race recovery path calls gateway refund before raising. |
| Boost multiplier exceeds CHECK constraint | DB CHECK `[1.0, 5.0]` rejects bad inserts; service clamps in `compute_provider_score` too. |
| LLM-based insights swap breaks contract | `ProviderInsight` dataclass is the public type; future ML returns the same shape. |

---

## 19. Out of scope (future plans)

- **Auctions** (bid-per-impression rather than flat boost). Adds `BoostBid` + auction-clearing worker.
- **Sponsored category slots** (admin-curated promo slots in category lists).
- **Subscriptions** (monthly "Pro" plan with always-on 1.2× boost). Adds `ProviderSubscription` + Stripe subscription wiring.
- **Geo-targeted boosts** (boost in metro X only). Extends `ProviderBoost.metadata_json` with `metro_slug[]` filter consumed by the ranking integration.
- **Boost ROI dashboard** ("Your boost generated X bookings worth Y") — needs impression tracking + attribution model.
- **Real Stripe Connect integration** (Plan 11 Phase 4 owns this; this plan abstracts cleanly to swap).
