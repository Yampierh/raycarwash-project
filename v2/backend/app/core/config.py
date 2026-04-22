from __future__ import annotations

from functools import lru_cache

from pydantic import AnyUrl, Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------------------------------------------------------------- #
    #  Application                                                      #
    # ---------------------------------------------------------------- #
    PROJECT_NAME: str = Field(default="RayCarwash API v2")
    API_VERSION: str  = Field(default="v2")
    DEBUG: bool       = Field(default=False)
    APP_BASE_URL: str = Field(default="https://api.raycarwash.com")

    # ---------------------------------------------------------------- #
    #  Database                                                         #
    # ---------------------------------------------------------------- #
    DATABASE_URL: PostgresDsn = Field(...)
    DB_POOL_SIZE: int    = Field(default=10,   ge=1,  le=50)
    DB_MAX_OVERFLOW: int = Field(default=20,   ge=0,  le=100)
    DB_POOL_TIMEOUT: int = Field(default=30,   ge=5)
    DB_POOL_RECYCLE: int = Field(default=1800)

    # ---------------------------------------------------------------- #
    #  Redis (v2)                                                       #
    # ---------------------------------------------------------------- #
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL. Use redis://:<password>@host:port/db in production.",
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=20, ge=1, le=100)

    # ---------------------------------------------------------------- #
    #  H3 Geospatial (v2)                                              #
    # ---------------------------------------------------------------- #
    H3_RESOLUTION_SEARCH: int = Field(
        default=7,
        ge=0, le=15,
        description="H3 resolution for k-ring search. Resolution 7 ≈ 5.16 km² per cell.",
    )
    H3_RESOLUTION_STORE: int = Field(
        default=9,
        ge=0, le=15,
        description="H3 resolution for precise detailer location storage. Resolution 9 ≈ 0.1 km².",
    )
    H3_MILES_PER_RING: float = Field(
        default=2.5,
        description="Approximate miles covered per k-ring expansion at H3_RESOLUTION_SEARCH.",
    )
    DETAILER_ACTIVE_TTL_SECONDS: int = Field(
        default=300,
        description="Redis TTL for active:{detailer_id} key. Detailer removed from search after this idle time.",
    )

    # ---------------------------------------------------------------- #
    #  Surge Pricing (v2)                                              #
    # ---------------------------------------------------------------- #
    SURGE_SEARCH_RADIUS_MILES: float = Field(
        default=10.0,
        description="Radius used to count active detailers when computing surge multiplier.",
    )
    # Tiers: list of (max_detailer_count, surge_multiplier)
    # If active_count < tier.count → apply tier.multiplier
    SURGE_TIER_CRITICAL_MAX: int   = Field(default=2,   description="< this count → critical surge")
    SURGE_TIER_CRITICAL_MULT: float = Field(default=2.0)
    SURGE_TIER_HIGH_MAX: int       = Field(default=4,   description="< this count → high surge")
    SURGE_TIER_HIGH_MULT: float    = Field(default=1.5)
    SURGE_TIER_MODERATE_MAX: int   = Field(default=8,   description="< this count → moderate surge")
    SURGE_TIER_MODERATE_MULT: float = Field(default=1.2)

    # ---------------------------------------------------------------- #
    #  Assignment Engine (v2)                                          #
    # ---------------------------------------------------------------- #
    ASSIGNMENT_OFFER_TTL_SECONDS: int = Field(
        default=15,
        description="Seconds a detailer has to accept/decline an offer before timeout.",
    )
    ASSIGNMENT_MAX_CANDIDATES: int = Field(
        default=3,
        description="Maximum detailers to attempt before marking appointment as NO_DETAILER_FOUND.",
    )
    ASSIGNMENT_SCORE_DISTANCE_WEIGHT: float  = Field(default=0.4)
    ASSIGNMENT_SCORE_RATING_WEIGHT: float    = Field(default=0.4)
    ASSIGNMENT_SCORE_RESPONSE_WEIGHT: float  = Field(default=0.2)

    # ---------------------------------------------------------------- #
    #  Fireball Push Filter (v2)                                       #
    # ---------------------------------------------------------------- #
    FIREBALL_DISTANCE_THRESHOLD_METERS: float = Field(
        default=50.0,
        description="Minimum position change (meters) required to trigger a push broadcast.",
    )
    FIREBALL_HEADING_THRESHOLD_DEGREES: float = Field(
        default=10.0,
        description="Minimum heading change (degrees) required to trigger a push broadcast.",
    )

    # ---------------------------------------------------------------- #
    #  Fare Estimate (v2)                                              #
    # ---------------------------------------------------------------- #
    FARE_TOKEN_TTL_SECONDS: int = Field(
        default=900,
        description="TTL for fare tokens in Redis. Client must create ride within this window.",
    )

    # ---------------------------------------------------------------- #
    #  Security / JWT                                                   #
    # ---------------------------------------------------------------- #
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str             = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int  = Field(default=30,  ge=5)
    REFRESH_TOKEN_EXPIRE_DAYS: int    = Field(default=7,   ge=1)

    # ---------------------------------------------------------------- #
    #  Stripe                                                           #
    # ---------------------------------------------------------------- #
    STRIPE_SECRET_KEY: str          = Field(default="sk_test_placeholder")
    STRIPE_WEBHOOK_SECRET: str      = Field(default="whsec_placeholder")
    STRIPE_IDENTITY_WEBHOOK_SECRET: str = Field(default="whsec_placeholder")
    STRIPE_PUBLISHABLE_KEY: str     = Field(default="pk_test_placeholder")
    STRIPE_CURRENCY: str            = Field(default="usd")

    # ---------------------------------------------------------------- #
    #  Rate Limiting                                                    #
    # ---------------------------------------------------------------- #
    RATE_LIMIT_AUTH_PER_MINUTE: int = Field(default=10)
    RATE_LIMIT_API_PER_MINUTE: int  = Field(default=120)

    # ---------------------------------------------------------------- #
    #  Business Logic                                                   #
    # ---------------------------------------------------------------- #
    TRAVEL_BUFFER_MINUTES: int = Field(default=30)
    CANCELLATION_FULL_REFUND_HOURS: int     = Field(default=24)
    CANCELLATION_PARTIAL_REFUND_HOURS: int  = Field(default=2)
    CANCELLATION_PARTIAL_REFUND_PERCENT: int = Field(default=50, ge=0, le=100)
    MAX_REQUEST_BODY_BYTES: int = Field(default=5 * 1024 * 1024)

    # ---------------------------------------------------------------- #
    #  CORS                                                             #
    # ---------------------------------------------------------------- #
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8081"],
    )

    # ---------------------------------------------------------------- #
    #  WebAuthn                                                         #
    # ---------------------------------------------------------------- #
    WEBAUTHN_RP_ID: str                    = Field(default="raycarwash.com")
    WEBAUTHN_RP_NAME: str                  = Field(default="RayCarwash")
    WEBAUTHN_ORIGIN: str                   = Field(default="https://raycarwash.com")
    WEBAUTHN_CHALLENGE_EXPIRE_MINUTES: int = Field(default=5)
    ANDROID_SHA256_CERT: str               = Field(default="")

    # ---------------------------------------------------------------- #
    #  Validators                                                       #
    # ---------------------------------------------------------------- #
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_async_driver(cls, value: str) -> str:
        if isinstance(value, str) and "asyncpg" not in value:
            raise ValueError(
                "DATABASE_URL must use the asyncpg driver (postgresql+asyncpg://...)."
            )
        return value

    @field_validator("STRIPE_SECRET_KEY", mode="before")
    @classmethod
    def validate_stripe_key(cls, value: str) -> str:
        placeholders = {"sk_test_placeholder", "sk_live_placeholder", ""}
        if value in placeholders:
            import warnings
            warnings.warn("STRIPE_SECRET_KEY is a placeholder — payments disabled.", stacklevel=2)
            return value
        if not value.startswith(("sk_test_", "sk_live_", "rk_")):
            raise ValueError("STRIPE_SECRET_KEY must start with 'sk_test_', 'sk_live_', or 'rk_'.")
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
