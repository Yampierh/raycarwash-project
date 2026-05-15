"""
infrastructure/sms/console.py — Dev SMS adapter.

Logs the OTP to stdout. The mobile app's dev menu can read the same code
from the server log or, in test, the contact-change endpoint optionally
echoes the code back when RAYCARWASH_ENV=development.

Switch to TwilioSmsAdapter in production via app/core/dependencies.py.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("raycarwash.sms.console")


class ConsoleSmsAdapter:
    """Dev/test adapter — never instantiate in prod."""

    async def send_otp(self, to: str, code: str, *, ttl_minutes: int) -> None:
        logger.warning(
            "[DEV-SMS] OTP for %s → %s (valid %d min). NEVER use ConsoleSmsAdapter in production.",
            to,
            code,
            ttl_minutes,
        )
