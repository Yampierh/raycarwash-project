"""SMS adapters — selected by RAYCARWASH_ENV via app/core/dependencies.py.

The protocol is intentionally narrow: send_otp(to, code) is the only call
the Profile contact-change flow needs. Marketing SMS (booking reminders,
etc.) is a separate concern — different adapter when that lands.
"""

from infrastructure.sms.base import SmsAdapter, SmsDeliveryError  # noqa: F401
from infrastructure.sms.console import ConsoleSmsAdapter  # noqa: F401
