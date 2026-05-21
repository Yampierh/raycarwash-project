"""m_025 DB hardening + marketplace operational records

Adds production-grade DB enforcement around appointments, payments,
provider availability, cancellations, refunds, and provider payouts.
Also removes the accidental write:permissions grant from the client role.

Revision ID: m_025
Revises: m_024
Create Date: 2026-05-20
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "m_025"
down_revision = "m_024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── RBAC safety fix ───────────────────────────────────────────────
    op.execute(
        """
        DELETE FROM role_permissions rp
        USING roles r, permissions p
        WHERE rp.role_id = r.id
          AND rp.permission_id = p.id
          AND r.name = 'client'
          AND p.name = 'write:permissions'
        """
    )

    # ── Operational appointment records ───────────────────────────────
    op.create_table(
        "appointment_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_status", sa.String(30), nullable=True),
        sa.Column("new_status", sa.String(30), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_appointment_status_history_appointment_id", "appointment_status_history", ["appointment_id"])
    op.create_index("ix_appointment_status_history_appointment_created", "appointment_status_history", ["appointment_id", "created_at"])
    op.create_index("ix_appointment_status_history_actor_created", "appointment_status_history", ["actor_id", "created_at"])

    op.create_table(
        "appointment_cancellations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cancelled_by_role", sa.String(20), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("refund_amount_cents", sa.Integer(), nullable=True),
        sa.Column("refund_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("policy_code", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("appointment_id", name="uq_appointment_cancellations_appointment"),
        sa.CheckConstraint("refund_amount_cents IS NULL OR refund_amount_cents >= 0", name="ck_appointment_cancellations_refund_amount_nonnegative"),
        sa.CheckConstraint("refund_percent IS NULL OR (refund_percent >= 0 AND refund_percent <= 100)", name="ck_appointment_cancellations_refund_percent_range"),
    )
    op.create_index("ix_appointment_cancellations_cancelled_by", "appointment_cancellations", ["cancelled_by_user_id", "created_at"])

    # ── Provider availability overrides ───────────────────────────────
    op.create_table(
        "provider_availability_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="unavailable"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("ends_at > starts_at", name="ck_provider_availability_ends_after_starts"),
    )
    op.create_index("ix_provider_availability_exceptions_provider_profile_id", "provider_availability_exceptions", ["provider_profile_id"])
    op.create_index("ix_provider_availability_provider_start", "provider_availability_exceptions", ["provider_profile_id", "starts_at"])
    op.create_index("ix_provider_availability_window", "provider_availability_exceptions", ["starts_at", "ends_at"])

    # ── Refunds + payouts ─────────────────────────────────────────────
    op.create_table(
        "refunds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_ledger_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payment_ledger.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stripe_refund_id", sa.String(100), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="usd"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("stripe_refund_id", name="uq_refunds_stripe_refund_id"),
        sa.CheckConstraint("amount_cents >= 0", name="ck_refunds_amount_nonnegative"),
    )
    op.create_index("ix_refunds_appointment_id", "refunds", ["appointment_id"])
    op.create_index("ix_refunds_appointment_created", "refunds", ["appointment_id", "created_at"])
    op.create_index("ix_refunds_status_created", "refunds", ["status", "created_at"])

    op.create_table(
        "provider_payouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("stripe_payout_id", sa.String(100), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="usd"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("arrival_date", sa.Date(), nullable=True),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("stripe_payout_id", name="uq_provider_payouts_stripe_payout_id"),
        sa.CheckConstraint("amount_cents >= 0", name="ck_provider_payouts_amount_nonnegative"),
    )
    op.create_index("ix_provider_payouts_provider_profile_id", "provider_payouts", ["provider_profile_id"])
    op.create_index("ix_provider_payouts_provider_created", "provider_payouts", ["provider_profile_id", "created_at"])
    op.create_index("ix_provider_payouts_status_created", "provider_payouts", ["status", "created_at"])

    # ── Hot path indexes / dedupe constraints ─────────────────────────
    op.create_index("ix_appointments_client_scheduled", "appointments", ["client_id", "scheduled_time", "is_deleted"])
    op.create_index("ix_appointments_detailer_status_scheduled", "appointments", ["detailer_id", "status", "scheduled_time"])
    op.create_index("ix_documents_user_type", "documents", ["user_id", "type"])
    op.create_index("ix_documents_expires_at", "documents", ["expires_at"])
    op.create_index("ix_assignment_status_expires", "appointment_assignments", ["status", "offer_expires_at"])
    op.create_index("ix_fare_estimates_expires_at", "fare_estimates", ["expires_at"])
    op.create_index("ix_payment_ledger_type_created", "payment_ledger", ["entry_type", "created_at"])

    op.create_unique_constraint("uq_assignment_appointment_detailer", "appointment_assignments", ["appointment_id", "detailer_id"])
    op.create_unique_constraint("uq_appointment_vehicle_pair", "appointment_vehicles", ["appointment_id", "vehicle_id"])
    op.create_unique_constraint("uq_appointment_addon_pair", "appointment_addons", ["appointment_id", "addon_id"])

    # ── Data integrity checks ─────────────────────────────────────────
    for table_name, constraint_name, expression in [
        ("appointments", "ck_appointments_estimated_price_nonnegative", "estimated_price >= 0"),
        ("appointments", "ck_appointments_actual_price_nonnegative", "actual_price IS NULL OR actual_price >= 0"),
        ("appointments", "ck_appointments_service_latitude_range", "service_latitude IS NULL OR (service_latitude >= -90 AND service_latitude <= 90)"),
        ("appointments", "ck_appointments_service_longitude_range", "service_longitude IS NULL OR (service_longitude >= -180 AND service_longitude <= 180)"),
        ("appointment_vehicles", "ck_appointment_vehicles_price_nonnegative", "price_cents >= 0"),
        ("appointment_vehicles", "ck_appointment_vehicles_duration_positive", "duration_minutes > 0"),
        ("appointment_addons", "ck_appointment_addons_price_nonnegative", "price_cents >= 0"),
        ("appointment_addons", "ck_appointment_addons_duration_positive", "duration_minutes > 0"),
        ("provider_profiles", "ck_provider_profiles_years_nonnegative", "years_of_experience IS NULL OR years_of_experience >= 0"),
        ("provider_profiles", "ck_provider_profiles_radius_positive", "service_radius_miles > 0"),
        ("provider_profiles", "ck_provider_profiles_average_rating_range", "average_rating IS NULL OR (average_rating >= 0 AND average_rating <= 5)"),
        ("provider_profiles", "ck_provider_profiles_total_reviews_nonnegative", "total_reviews >= 0"),
        ("provider_profiles", "ck_provider_profiles_response_rate_range", "response_rate >= 0 AND response_rate <= 1"),
        ("provider_profiles", "ck_provider_profiles_earnings_lifetime_nonnegative", "earnings_lifetime_cents >= 0"),
        ("provider_profiles", "ck_provider_profiles_services_completed_nonnegative", "total_services_completed >= 0"),
        ("provider_profiles", "ck_provider_profiles_water_tank_nonnegative", "water_tank_gallons IS NULL OR water_tank_gallons >= 0"),
        ("services", "ck_services_base_price_nonnegative", "base_price_cents >= 0"),
        ("services", "ck_services_base_duration_positive", "base_duration_minutes > 0"),
        ("services", "ck_services_prices_nonnegative", "price_small >= 0 AND price_medium >= 0 AND price_large >= 0 AND price_xl >= 0"),
        ("services", "ck_services_durations_positive", "duration_small_minutes > 0 AND duration_medium_minutes > 0 AND duration_large_minutes > 0 AND duration_xl_minutes > 0"),
        ("addons", "ck_addons_price_nonnegative", "price_cents >= 0"),
        ("addons", "ck_addons_duration_nonnegative", "duration_minutes >= 0"),
        ("provider_services", "ck_provider_services_custom_price_nonnegative", "custom_price_cents IS NULL OR custom_price_cents >= 0"),
        ("fare_estimates", "ck_fare_estimates_base_price_nonnegative", "base_price_cents >= 0"),
        ("fare_estimates", "ck_fare_estimates_estimated_price_nonnegative", "estimated_price_cents >= 0"),
        ("fare_estimates", "ck_fare_estimates_surge_multiplier_min", "surge_multiplier >= 1"),
        ("fare_estimates", "ck_fare_estimates_nearby_count_nonnegative", "nearby_detailers_count >= 0"),
        ("user_addresses", "ck_user_addresses_latitude_range", "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)"),
        ("user_addresses", "ck_user_addresses_longitude_range", "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)"),
        ("payment_methods", "ck_payment_methods_exp_month_range", "exp_month IS NULL OR (exp_month >= 1 AND exp_month <= 12)"),
        ("payment_methods", "ck_payment_methods_exp_year_min", "exp_year IS NULL OR exp_year >= 2000"),
        ("documents", "ck_documents_size_nonnegative", "size_bytes IS NULL OR size_bytes >= 0"),
        ("client_profiles", "ck_client_profiles_total_appointments_nonnegative", "total_appointments_count >= 0"),
        ("client_profiles", "ck_client_profiles_total_spent_nonnegative", "total_spent_cents >= 0"),
        ("payment_ledger", "ck_payment_ledger_currency_lowercase", "currency = lower(currency)"),
        ("payment_ledger", "ck_payment_ledger_amount_nonnegative", "amount_cents >= 0"),
        ("ledger_seals", "ck_ledger_seals_entry_count_nonnegative", "entry_count >= 0"),
        ("ledger_seals", "ck_ledger_seals_sha256_length", "length(sha256_hash) = 64"),
    ]:
        op.create_check_constraint(constraint_name, table_name, expression)

    # ── Append-only ledger enforcement ────────────────────────────────
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_payment_ledger_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'payment_ledger is append-only; use ledger_revisions instead';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER prevent_payment_ledger_mutation
        BEFORE UPDATE OR DELETE ON payment_ledger
        FOR EACH ROW EXECUTE FUNCTION prevent_payment_ledger_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER prevent_payment_ledger_truncate
        BEFORE TRUNCATE ON payment_ledger
        FOR EACH STATEMENT EXECUTE FUNCTION prevent_payment_ledger_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS prevent_payment_ledger_truncate ON payment_ledger")
    op.execute("DROP TRIGGER IF EXISTS prevent_payment_ledger_mutation ON payment_ledger")
    op.execute("DROP FUNCTION IF EXISTS prevent_payment_ledger_mutation()")

    for table_name, constraint_name in [
        ("ledger_seals", "ck_ledger_seals_sha256_length"),
        ("ledger_seals", "ck_ledger_seals_entry_count_nonnegative"),
        ("payment_ledger", "ck_payment_ledger_currency_lowercase"),
        ("payment_ledger", "ck_payment_ledger_amount_nonnegative"),
        ("client_profiles", "ck_client_profiles_total_spent_nonnegative"),
        ("client_profiles", "ck_client_profiles_total_appointments_nonnegative"),
        ("documents", "ck_documents_size_nonnegative"),
        ("payment_methods", "ck_payment_methods_exp_year_min"),
        ("payment_methods", "ck_payment_methods_exp_month_range"),
        ("user_addresses", "ck_user_addresses_longitude_range"),
        ("user_addresses", "ck_user_addresses_latitude_range"),
        ("fare_estimates", "ck_fare_estimates_nearby_count_nonnegative"),
        ("fare_estimates", "ck_fare_estimates_surge_multiplier_min"),
        ("fare_estimates", "ck_fare_estimates_estimated_price_nonnegative"),
        ("fare_estimates", "ck_fare_estimates_base_price_nonnegative"),
        ("provider_services", "ck_provider_services_custom_price_nonnegative"),
        ("addons", "ck_addons_duration_nonnegative"),
        ("addons", "ck_addons_price_nonnegative"),
        ("services", "ck_services_durations_positive"),
        ("services", "ck_services_prices_nonnegative"),
        ("services", "ck_services_base_duration_positive"),
        ("services", "ck_services_base_price_nonnegative"),
        ("provider_profiles", "ck_provider_profiles_water_tank_nonnegative"),
        ("provider_profiles", "ck_provider_profiles_services_completed_nonnegative"),
        ("provider_profiles", "ck_provider_profiles_earnings_lifetime_nonnegative"),
        ("provider_profiles", "ck_provider_profiles_response_rate_range"),
        ("provider_profiles", "ck_provider_profiles_total_reviews_nonnegative"),
        ("provider_profiles", "ck_provider_profiles_average_rating_range"),
        ("provider_profiles", "ck_provider_profiles_radius_positive"),
        ("provider_profiles", "ck_provider_profiles_years_nonnegative"),
        ("appointment_addons", "ck_appointment_addons_duration_positive"),
        ("appointment_addons", "ck_appointment_addons_price_nonnegative"),
        ("appointment_vehicles", "ck_appointment_vehicles_duration_positive"),
        ("appointment_vehicles", "ck_appointment_vehicles_price_nonnegative"),
        ("appointments", "ck_appointments_service_longitude_range"),
        ("appointments", "ck_appointments_service_latitude_range"),
        ("appointments", "ck_appointments_actual_price_nonnegative"),
        ("appointments", "ck_appointments_estimated_price_nonnegative"),
    ]:
        op.drop_constraint(constraint_name, table_name, type_="check")

    op.drop_constraint("uq_appointment_addon_pair", "appointment_addons", type_="unique")
    op.drop_constraint("uq_appointment_vehicle_pair", "appointment_vehicles", type_="unique")
    op.drop_constraint("uq_assignment_appointment_detailer", "appointment_assignments", type_="unique")

    op.drop_index("ix_assignment_status_expires", table_name="appointment_assignments")
    op.drop_index("ix_payment_ledger_type_created", table_name="payment_ledger")
    op.drop_index("ix_fare_estimates_expires_at", table_name="fare_estimates")
    op.drop_index("ix_documents_expires_at", table_name="documents")
    op.drop_index("ix_documents_user_type", table_name="documents")
    op.drop_index("ix_appointments_detailer_status_scheduled", table_name="appointments")
    op.drop_index("ix_appointments_client_scheduled", table_name="appointments")

    op.drop_index("ix_provider_payouts_status_created", table_name="provider_payouts")
    op.drop_index("ix_provider_payouts_provider_created", table_name="provider_payouts")
    op.drop_index("ix_provider_payouts_provider_profile_id", table_name="provider_payouts")
    op.drop_table("provider_payouts")

    op.drop_index("ix_refunds_status_created", table_name="refunds")
    op.drop_index("ix_refunds_appointment_created", table_name="refunds")
    op.drop_index("ix_refunds_appointment_id", table_name="refunds")
    op.drop_table("refunds")

    op.drop_index("ix_provider_availability_window", table_name="provider_availability_exceptions")
    op.drop_index("ix_provider_availability_provider_start", table_name="provider_availability_exceptions")
    op.drop_index("ix_provider_availability_exceptions_provider_profile_id", table_name="provider_availability_exceptions")
    op.drop_table("provider_availability_exceptions")

    op.drop_index("ix_appointment_cancellations_cancelled_by", table_name="appointment_cancellations")
    op.drop_table("appointment_cancellations")

    op.drop_index("ix_appointment_status_history_actor_created", table_name="appointment_status_history")
    op.drop_index("ix_appointment_status_history_appointment_created", table_name="appointment_status_history")
    op.drop_index("ix_appointment_status_history_appointment_id", table_name="appointment_status_history")
    op.drop_table("appointment_status_history")

    # Restore previous RBAC state only if this migration is rolled back.
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id, assigned_at)
        SELECT r.id, p.id, NOW()
        FROM roles r, permissions p
        WHERE r.name = 'client'
          AND p.name = 'write:permissions'
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
        """
    )
