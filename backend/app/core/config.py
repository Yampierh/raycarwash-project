# app/core/config.py  —  Sprint 3
#
# ADDITIONS:
#   - STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET
#   - REFRESH_TOKEN_EXPIRE_DAYS (was already there, explicit comment added)
#   - RATE_LIMIT_* settings for slowapi
#   - APP_BASE_URL for generating absolute links in emails

from __future__ import annotations

from functools import lru_cache

from pydantic import AnyUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Single source of truth for all environment-driven configuration.

    All fields are sourced from environment variables (or .env in dev).
    Pydantic-settings raises ValidationError at import time on any
    missing required field — fail fast, never at runtime.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------------------------------------------------------- #
    #  Application                                                      #
    # ---------------------------------------------------------------- #
    PROJECT_NAME: str = Field(default="RayCarwash API")
    API_VERSION: str  = Field(default="v1")
    DEBUG: bool       = Field(default=False, description="Never True in production.")
    APP_BASE_URL: str = Field(
        default="https://api.raycarwash.com",
        description="Canonical base URL — used in email links, webhooks, etc.",
    )

    # ---------------------------------------------------------------- #
    #  Database                                                         #
    # ---------------------------------------------------------------- #
    DATABASE_URL: PostgresDsn = Field(
        ...,
        description=(
            "Must use asyncpg driver. "
            "Example: postgresql+asyncpg://user:pass@host:5432/raycarwash"
        ),
    )
    DB_POOL_SIZE: int    = Field(default=10,   ge=1,  le=50)
    DB_MAX_OVERFLOW: int = Field(default=20,   ge=0,  le=100)
    DB_POOL_TIMEOUT: int = Field(default=30,   ge=5)
    DB_POOL_RECYCLE: int = Field(default=1800)

    # ---------------------------------------------------------------- #
    #  Security / JWT                                                   #
    # ---------------------------------------------------------------- #
    SECRET_KEY: str = Field(
        ...,
        min_length=32,
        description="256-bit hex. Generate: openssl rand -hex 32",
    )
    JWT_ALGORITHM: str             = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int  = Field(default=30,  ge=5)
    REFRESH_TOKEN_EXPIRE_DAYS: int    = Field(default=7,   ge=1)

    # ---------------------------------------------------------------- #
    #  Stripe (Sprint 3)                                               #
    # ---------------------------------------------------------------- #
    STRIPE_SECRET_KEY: str = Field(
        default="sk_test_placeholder",
        description=(
            "Stripe secret key. Use sk_test_* in dev, sk_live_* in prod. "
            "NEVER commit the live key."
        ),
    )
    STRIPE_WEBHOOK_SECRET: str = Field(
        default="whsec_placeholder",
        description=(
            "From Stripe Dashboard → Webhooks → Signing secret. "
            "Used to verify that webhook payloads originated from Stripe."
        ),
    )
    STRIPE_IDENTITY_WEBHOOK_SECRET: str = Field(
        default="whsec_placeholder",
        description=(
            "Separate signing secret for the Stripe Identity webhook endpoint. "
            "From Stripe Dashboard → Webhooks → Identity webhook signing secret."
        ),
    )
    STRIPE_PUBLISHABLE_KEY: str = Field(
        default="pk_test_placeholder",
        description="Stripe publishable key. Sent to the frontend.",
    )
    STRIPE_CURRENCY: str = Field(default="usd")

    # ---------------------------------------------------------------- #
    #  Rate limiting (slowapi)                                         #
    # ---------------------------------------------------------------- #
    RATE_LIMIT_AUTH_PER_MINUTE: int = Field(
        default=10,
        description="Max login attempts per IP per minute on POST /auth/token.",
    )
    RATE_LIMIT_API_PER_MINUTE: int = Field(
        default=120,
        description="General API rate limit per authenticated user per minute.",
    )

    # ---------------------------------------------------------------- #
    #  Business logic                                                   #
    # ---------------------------------------------------------------- #
    TRAVEL_BUFFER_MINUTES: int = Field(
        default=30,
        description="Mandatory travel gap between detailer appointments.",
    )

    # ---- Cancellation & Refund Policy (Sprint 4) ----
    # Tiered refund windows:
    #   ≥ FULL_REFUND_HOURS before appointment  → 100% refund
    #   ≥ PARTIAL_REFUND_HOURS before           → PARTIAL_REFUND_PERCENT % refund
    #   < PARTIAL_REFUND_HOURS before           → no refund
    CANCELLATION_FULL_REFUND_HOURS: int = Field(
        default=24,
        description=(
            "Hours before appointment start where cancellation earns "
            "a 100%% refund. Default: 24 hours."
        ),
    )
    CANCELLATION_PARTIAL_REFUND_HOURS: int = Field(
        default=2,
        description=(
            "Hours before appointment start where cancellation earns "
            "a partial refund (see PARTIAL_REFUND_PERCENT). Default: 2 hours."
        ),
    )
    CANCELLATION_PARTIAL_REFUND_PERCENT: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Percentage of estimated_price refunded in the partial window. Default: 50%%.",
    )

    # ---- Request body size limit (Sprint 4) ----
    MAX_REQUEST_BODY_BYTES: int = Field(
        default=5 * 1024 * 1024,  # 5 MB
        description=(
            "Maximum allowed Content-Length for incoming requests. "
            "Requests exceeding this are rejected with HTTP 413 before "
            "the body is read, protecting against payload-based DoS."
        ),
    )

    # ---------------------------------------------------------------- #
    #  Social login (Sprint 5)                                         #
    # ---------------------------------------------------------------- #
    # ---------------------------------------------------------------- #
    #  Email (Sprint 5)                                                #
    # ---------------------------------------------------------------- #
    SMTP_ENABLED: bool = Field(
        default=False,
        description=(
            "Set to True to send real emails. Requires SMTP_HOST + credentials. "
            "When False, reset links are logged to stdout (dev mode)."
        ),
    )
    SMTP_HOST: str = Field(default="smtp.gmail.com", description="SMTP server hostname.")
    SMTP_PORT: int = Field(default=587, description="SMTP port (587=STARTTLS, 465=SSL).")
    SMTP_USERNAME: str = Field(default="", description="SMTP auth username (usually email).")
    SMTP_PASSWORD: str = Field(default="", description="SMTP auth password or app password.")
    SMTP_FROM_EMAIL: str = Field(
        default="noreply@raycarwash.com",
        description="From address for transactional emails.",
    )
    SMTP_FROM_NAME: str = Field(default="RayCarwash", description="Display name in From header.")

    GOOGLE_CLIENT_ID: str = Field(
        default="",
        description=(
            "Google OAuth2 client ID. When set, the Google token's 'issued_to' "
            "claim is verified against this value (recommended for production). "
            "Leave empty to skip audience verification (dev/test only)."
        ),
    )
    APPLE_BUNDLE_ID: str = Field(
        default="com.raycarwash.app",
        description=(
            "Apple app bundle ID used as the expected 'aud' claim when verifying "
            "Apple identity tokens. Must match the bundle ID in App Store Connect."
        ),
    )

    # ---------------------------------------------------------------- #
    #  WebAuthn / FIDO2 (Passkeys)                                     #
    # ---------------------------------------------------------------- #
    WEBAUTHN_RP_ID: str = Field(
        default="raycarwash.com",
        description=(
            "Relying Party ID — must be a registrable domain suffix of the origin. "
            "E.g. 'raycarwash.com'. Used in both iOS Associated Domains and Android DAL."
        ),
    )
    WEBAUTHN_RP_NAME: str = Field(
        default="RayCarwash",
        description="Human-readable Relying Party name shown in the passkey prompt.",
    )
    WEBAUTHN_ORIGIN: str = Field(
        default="https://raycarwash.com",
        description=(
            "Expected origin for WebAuthn assertions. "
            "For native apps this is the https:// origin tied to Associated Domains."
        ),
    )
    WEBAUTHN_CHALLENGE_EXPIRE_MINUTES: int = Field(
        default=5,
        description="TTL for WebAuthn challenge JWT tokens.",
    )
    ANDROID_SHA256_CERT: str = Field(
        default="",
        description=(
            "SHA-256 fingerprint of the Android signing certificate (colon-separated hex). "
            "Used to generate /.well-known/assetlinks.json for Digital Asset Links."
        ),
    )

    # ---------------------------------------------------------------- #
    #  CORS                                                             #
    # ---------------------------------------------------------------- #
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8081"],
        description="Expo dev server runs on 8081 by default.",
    )

    # ---------------------------------------------------------------- #
    #  Validators                                                       #
    # ---------------------------------------------------------------- #
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_async_driver(cls, value: str) -> str:
        if isinstance(value, str) and "asyncpg" not in value:
            raise ValueError(
                "DATABASE_URL must use the asyncpg driver "
                "(postgresql+asyncpg://...). "
                "psycopg2 with async_engine causes deadlocks."
            )
        return value

    @field_validator("STRIPE_SECRET_KEY", mode="before")
    @classmethod
    def validate_stripe_secret_key(cls, value: str) -> str:
        _placeholders = {"sk_test_placeholder", "sk_live_placeholder", ""}
        if value in _placeholders:
            import warnings
            warnings.warn(
                "STRIPE_SECRET_KEY is a placeholder. "
                "Payments will not work until a real key is set.",
                stacklevel=2,
            )
            return value
        if not value.startswith(("sk_test_", "sk_live_", "rk_")):
            raise ValueError(
                "STRIPE_SECRET_KEY must start with 'sk_test_', 'sk_live_', or 'rk_'. "
                "Check your Stripe Dashboard for the correct key."
            )
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Cached Settings singleton.

    @lru_cache delays instantiation until first call — tests can
    monkeypatch env vars before importing anything that calls this.
    """
    return Settings()  # type: ignore[call-arg]