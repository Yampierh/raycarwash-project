"""
app/core/dependencies.py — FastAPI dependency factories that bind external
adapters according to the active environment.

Adapters returned here implement the protocols in `infrastructure/storage/`,
`infrastructure/email/`, etc. Routers and services depend on the protocol —
never on a concrete adapter — so production deployments swap implementations
by flipping `RAYCARWASH_ENV` without changing handler code.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from infrastructure.storage.base import FileStorageAdapter
from infrastructure.storage.local import LocalStorageAdapter


# Logical bucket names. Two buckets per ADR-008: public CDN-served and
# private SSE-KMS-served. In LocalStorageAdapter they become subdirectories
# of STORAGE_LOCAL_PATH.
BUCKET_PUBLIC = "public-assets"
BUCKET_PRIVATE = "private-docs"


@lru_cache(maxsize=4)
def _build_adapter(bucket: str) -> FileStorageAdapter:
    """Cache one adapter instance per bucket — they're stateless."""
    env = get_settings().RAYCARWASH_ENV
    if env == "production":
        # TODO(prod) — `infrastructure/storage/s3.py` is not implemented.
        # When implementing:
        #   1. Create `class S3StorageAdapter` matching the FileStorageAdapter
        #      Protocol in `infrastructure/storage/base.py`.
        #   2. Use boto3 + `generate_presigned_url(ClientMethod="put_object")`
        #      for `generate_upload_url`; HEAD for `head_object`;
        #      `generate_presigned_url("get_object", ...)` for downloads.
        #   3. Public bucket (`bucket=BUCKET_PUBLIC`) → CloudFront-signed URLs
        #      with 24h TTL. Private bucket (`bucket=BUCKET_PRIVATE`) →
        #      SSE-KMS + 1h presigned URLs. See plan §9, ADR-008.
        #   4. Replace the raise below with:
        #         from infrastructure.storage.s3 import S3StorageAdapter
        #         return S3StorageAdapter(bucket=bucket)
        raise RuntimeError(
            "S3StorageAdapter is not implemented yet. "
            "Either implement infrastructure/storage/s3.py or set RAYCARWASH_ENV=development."
        )
    return LocalStorageAdapter(bucket=bucket)


def get_public_storage() -> FileStorageAdapter:
    """Avatars, covers, vehicle photos, provider portfolio."""
    return _build_adapter(BUCKET_PUBLIC)


def get_private_storage() -> FileStorageAdapter:
    """KYC docs, insurance, exports — encrypted at rest in production."""
    return _build_adapter(BUCKET_PRIVATE)


# ─── SMS adapter (Phase 3) ───────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_sms_adapter():
    """ConsoleSmsAdapter in dev (OTP logged to stdout), TwilioSmsAdapter
    in prod (currently raises — see infrastructure/sms/twilio.py)."""
    from infrastructure.sms.console import ConsoleSmsAdapter

    env = get_settings().RAYCARWASH_ENV
    if env == "production":
        from infrastructure.sms.twilio import TwilioSmsAdapter
        return TwilioSmsAdapter()
    return ConsoleSmsAdapter()


# ─── Payment method adapter (Phase 4 chunk U) ────────────────────────────────


@lru_cache(maxsize=1)
def get_payment_method_adapter():
    """StripeStubAdapter when STRIPE_SECRET_KEY is a placeholder (dev/CI
    bootstrap without keys). StripeTestAdapter when a real sk_test_* or
    sk_live_* key is configured — same code runs against test and live.

    The stub matches the existing PaymentService._is_stub_key() escape
    hatch so the whole payments domain switches stub→real together when
    keys are supplied."""
    from app.core.config import get_settings as _gs
    s = _gs()
    placeholder = s.STRIPE_SECRET_KEY in (
        "sk_test_placeholder", "sk_live_placeholder", ""
    )
    if placeholder:
        from infrastructure.payments.stripe_stub import StripeStubAdapter
        return StripeStubAdapter()
    from infrastructure.payments.stripe_test import StripeTestAdapter
    return StripeTestAdapter()


# ─── Geocoding adapter (Phase 4) ─────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_geocoding_adapter():
    """NominatimAdapter in dev (free OSM, rate-limited 1 req/s).
    GoogleMapsGeocodingAdapter in prod (currently raises — see
    infrastructure/geocoding/google.py for the TODO checklist)."""
    from infrastructure.geocoding.nominatim import NominatimAdapter

    env = get_settings().RAYCARWASH_ENV
    if env == "production":
        from infrastructure.geocoding.google import GoogleMapsGeocodingAdapter
        return GoogleMapsGeocodingAdapter()
    return NominatimAdapter()
