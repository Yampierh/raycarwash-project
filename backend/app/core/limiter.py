# app/core/limiter.py
#
# Shared slowapi Limiter instance attached to app.state in main.py.
# Import from here in every router that needs rate limiting.
# Request MUST be the first parameter of any rate-limited handler.

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],   # global safety net
)
