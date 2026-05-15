"""
infrastructure/sms/twilio.py — Production SMS adapter (TODO).

Placeholder so app/core/dependencies.py can import + return the class
when RAYCARWASH_ENV=production. The constructor raises so misconfigured
deploys fail loud at startup instead of after the first OTP request.

TODO(prod) — implement against the Twilio REST API:
  1. pip install twilio in requirements.txt (NOT a global install — the
     adapter should be lazy-imported so dev environments don't pull
     Twilio's transitive deps).
  2. Read TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER
     (Messaging Service SID preferred) from Settings — they're already
     documented as TODO blocks in .env.example.
  3. Use `client.messages.create(to=..., from_=..., body=...)` inside
     `asyncio.to_thread` since the Twilio SDK is synchronous.
  4. Translate twilio.base.exceptions.TwilioRestException to
     SmsDeliveryError so callers don't import Twilio types.
"""
from __future__ import annotations

from infrastructure.sms.base import SmsDeliveryError


class TwilioSmsAdapter:
    """Not implemented yet. Constructor raises with a precise message so
    the production deploy crashes at startup, not at the first OTP."""

    def __init__(self) -> None:
        # TODO(prod) — wire Twilio per the docstring above and delete this raise.
        raise NotImplementedError(
            "TwilioSmsAdapter is not implemented yet. "
            "Either implement infrastructure/sms/twilio.py (see module "
            "docstring for the recipe) or keep RAYCARWASH_ENV=development "
            "so ConsoleSmsAdapter is selected."
        )

    async def send_otp(self, to: str, code: str, *, ttl_minutes: int) -> None:
        raise SmsDeliveryError("TwilioSmsAdapter not implemented")
