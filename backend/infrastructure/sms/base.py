"""
infrastructure/sms/base.py — SMS adapter Protocol.

Concrete adapters: ConsoleSmsAdapter (dev, logs OTP to stdout) and
TwilioSmsAdapter (prod, TODO). Picked by environment in
app/core/dependencies.py.
"""
from __future__ import annotations

from typing import Protocol


class SmsDeliveryError(Exception):
    """Raised when the adapter could not hand the message to its carrier."""


class SmsAdapter(Protocol):
    """The minimum surface Phase 3 needs. Future phases (booking SMS, marketing)
    can extend with additional methods on a separate adapter — keep this one
    tight."""

    async def send_otp(self, to: str, code: str, *, ttl_minutes: int) -> None:
        """Deliver a one-time code to `to` (E.164). Idempotent at the
        adapter level (Twilio dedupes via MessagingServiceSid + body)."""
