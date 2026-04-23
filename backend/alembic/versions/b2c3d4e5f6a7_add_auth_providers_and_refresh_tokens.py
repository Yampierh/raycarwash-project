"""add auth_providers and refresh_tokens tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-23

Replaces google_id / apple_id columns on users with a normalised
auth_providers table.  Adds refresh_tokens for stateful rotation with
replay-attack / token-theft detection.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. auth_providers                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "auth_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_uid", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(254), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_uid", name="uq_auth_providers_provider_uid"),
    )
    op.create_index("ix_auth_providers_user_id", "auth_providers", ["user_id"])

    # ------------------------------------------------------------------ #
    # 2. refresh_tokens                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    # ------------------------------------------------------------------ #
    # 3. Migrate existing social data                                     #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        INSERT INTO auth_providers (id, user_id, provider, provider_uid, provider_email)
        SELECT gen_random_uuid(), id, 'google', google_id, email
        FROM users
        WHERE google_id IS NOT NULL AND is_deleted = false
        """
    )
    op.execute(
        """
        INSERT INTO auth_providers (id, user_id, provider, provider_uid, provider_email)
        SELECT gen_random_uuid(), id, 'apple', apple_id, email
        FROM users
        WHERE apple_id IS NOT NULL AND is_deleted = false
        """
    )

    # ------------------------------------------------------------------ #
    # 4. Drop legacy columns                                              #
    # ------------------------------------------------------------------ #
    op.drop_index("ix_users_google_id", table_name="users", if_exists=True)
    op.drop_index("ix_users_apple_id", table_name="users", if_exists=True)
    op.drop_column("users", "google_id")
    op.drop_column("users", "apple_id")


def downgrade() -> None:
    # Restore columns
    op.add_column(
        "users",
        sa.Column("google_id", sa.String(128), nullable=True, unique=True),
    )
    op.add_column(
        "users",
        sa.Column("apple_id", sa.String(128), nullable=True, unique=True),
    )
    op.create_index("ix_users_google_id", "users", ["google_id"])
    op.create_index("ix_users_apple_id", "users", ["apple_id"])

    # Restore data from auth_providers
    op.execute(
        """
        UPDATE users u
        SET google_id = ap.provider_uid
        FROM auth_providers ap
        WHERE ap.user_id = u.id AND ap.provider = 'google'
        """
    )
    op.execute(
        """
        UPDATE users u
        SET apple_id = ap.provider_uid
        FROM auth_providers ap
        WHERE ap.user_id = u.id AND ap.provider = 'apple'
        """
    )

    # Drop new tables
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_auth_providers_user_id", table_name="auth_providers")
    op.drop_table("auth_providers")
