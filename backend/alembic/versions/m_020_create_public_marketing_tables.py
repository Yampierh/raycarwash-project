"""m_020 create public marketing tables

Plan 19 (Track 1) — six tables backing the marketing portal at
`web/portal/`. All tables are soft-delete compatible (TimestampMixin
columns) per AGENTS.md project convention.

Source of truth for shape: `domains/public/models.py`.

Tables created:

  - testimonials         quotes by clients/detailers used on landing pages
  - faq                  Q&A grouped by audience enum
  - coverage_zones       SVG circles for the Landing.tsx coverage map
  - coverage_zips        ZIP → zone mapping (PK is the ZIP itself)
  - contact_submissions  append-only inbox for the public contact form
  - waitlist_entries     append-only waitlist (mechanic vertical etc.),
                         UNIQUE(email) enforced

Enums created:

  - testimonial_role_enum  (client | detailer)
  - faq_category_enum      (rider | detailer | mechanic | provider)
  - waitlist_role_enum     (mechanic | detailer | provider)

Indexes follow the ORM definitions: filterable composite indexes on the
columns the contract endpoints query most heavily.

Revision ID: m_020
Revises: m_019
Create Date: 2026-05-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_020"
down_revision = "m_019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────
    testimonial_role = postgresql.ENUM(
        "client", "detailer", name="testimonial_role_enum",
    )
    faq_category = postgresql.ENUM(
        "rider", "detailer", "mechanic", "provider", name="faq_category_enum",
    )
    waitlist_role = postgresql.ENUM(
        "mechanic", "detailer", "provider", name="waitlist_role_enum",
    )
    testimonial_role.create(op.get_bind(), checkfirst=True)
    faq_category.create(op.get_bind(), checkfirst=True)
    waitlist_role.create(op.get_bind(), checkfirst=True)

    # ── testimonials ──────────────────────────────────────────────────
    op.create_table(
        "testimonials",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(name="testimonial_role_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("meta", sa.String(255), nullable=True),
        sa.Column(
            "featured", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column(
            "sort_order", sa.Integer(),
            nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active", sa.Boolean(),
            nullable=False, server_default=sa.text("true"),
        ),
        # TimestampMixin
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "is_deleted", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "rating BETWEEN 1 AND 5", name="ck_testimonials_rating_range",
        ),
    )
    op.create_index(
        "ix_testimonials_role_featured",
        "testimonials",
        ["role", "featured", "is_deleted"],
    )
    op.create_index("ix_testimonials_sort", "testimonials", ["sort_order"])
    op.create_index("ix_testimonials_is_deleted", "testimonials", ["is_deleted"])

    # ── faq ───────────────────────────────────────────────────────────
    op.create_table(
        "faq",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "category",
            postgresql.ENUM(name="faq_category_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "sort_order", sa.Integer(),
            nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active", sa.Boolean(),
            nullable=False, server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "is_deleted", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_faq_category_sort", "faq", ["category", "sort_order", "is_deleted"],
    )
    op.create_index("ix_faq_is_deleted", "faq", ["is_deleted"])

    # ── coverage_zones ────────────────────────────────────────────────
    op.create_table(
        "coverage_zones",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "is_primary", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("svg_cx", sa.SmallInteger(), nullable=False),
        sa.Column("svg_cy", sa.SmallInteger(), nullable=False),
        sa.Column("svg_r", sa.SmallInteger(), nullable=False),
        sa.Column(
            "sort_order", sa.Integer(),
            nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active", sa.Boolean(),
            nullable=False, server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "is_deleted", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("name", name="uq_coverage_zones_name"),
    )
    op.create_index(
        "ix_coverage_zones_active_primary",
        "coverage_zones",
        ["is_active", "is_primary"],
    )
    op.create_index("ix_coverage_zones_sort", "coverage_zones", ["sort_order"])
    op.create_index(
        "ix_coverage_zones_is_deleted", "coverage_zones", ["is_deleted"],
    )

    # ── coverage_zips ─────────────────────────────────────────────────
    op.create_table(
        "coverage_zips",
        sa.Column("zip", sa.String(5), primary_key=True),
        sa.Column("zone_name", sa.String(120), nullable=False),
        sa.Column("eta_min", sa.Integer(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(),
            nullable=False, server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "is_deleted", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_coverage_zips_zone", "coverage_zips", ["zone_name", "is_active"],
    )
    op.create_index(
        "ix_coverage_zips_is_deleted", "coverage_zips", ["is_deleted"],
    )

    # ── contact_submissions ───────────────────────────────────────────
    op.create_table(
        "contact_submissions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "is_deleted", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_contact_submissions_email_created",
        "contact_submissions",
        ["email", "created_at"],
    )
    op.create_index(
        "ix_contact_submissions_created", "contact_submissions", ["created_at"],
    )
    op.create_index(
        "ix_contact_submissions_is_deleted",
        "contact_submissions",
        ["is_deleted"],
    )

    # ── waitlist_entries ──────────────────────────────────────────────
    op.create_table(
        "waitlist_entries",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            primary_key=True, server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(name="waitlist_role_enum", create_type=False),
            nullable=False,
            server_default="mechanic",
        ),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "is_deleted", sa.Boolean(),
            nullable=False, server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email", name="uq_waitlist_entries_email"),
    )
    op.create_index(
        "ix_waitlist_entries_role_created",
        "waitlist_entries",
        ["role", "created_at"],
    )
    op.create_index(
        "ix_waitlist_entries_is_deleted",
        "waitlist_entries",
        ["is_deleted"],
    )


def downgrade() -> None:
    op.drop_index("ix_waitlist_entries_is_deleted", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_role_created", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")

    op.drop_index("ix_contact_submissions_is_deleted", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_created", table_name="contact_submissions")
    op.drop_index("ix_contact_submissions_email_created", table_name="contact_submissions")
    op.drop_table("contact_submissions")

    op.drop_index("ix_coverage_zips_is_deleted", table_name="coverage_zips")
    op.drop_index("ix_coverage_zips_zone", table_name="coverage_zips")
    op.drop_table("coverage_zips")

    op.drop_index("ix_coverage_zones_is_deleted", table_name="coverage_zones")
    op.drop_index("ix_coverage_zones_sort", table_name="coverage_zones")
    op.drop_index("ix_coverage_zones_active_primary", table_name="coverage_zones")
    op.drop_table("coverage_zones")

    op.drop_index("ix_faq_is_deleted", table_name="faq")
    op.drop_index("ix_faq_category_sort", table_name="faq")
    op.drop_table("faq")

    op.drop_index("ix_testimonials_is_deleted", table_name="testimonials")
    op.drop_index("ix_testimonials_sort", table_name="testimonials")
    op.drop_index("ix_testimonials_role_featured", table_name="testimonials")
    op.drop_table("testimonials")

    # Enums last (referenced by columns above).
    postgresql.ENUM(name="waitlist_role_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="faq_category_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="testimonial_role_enum").drop(op.get_bind(), checkfirst=True)
