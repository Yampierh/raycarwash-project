# app/core/limiter.py  —  Sprint 4
#
# Shared slowapi Limiter instance.
#
# WHY a separate module?
# slowapi requires the same Limiter instance to be:
#   1. Attached to app.state.limiter  (done in main.py)
#   2. Used as the decorator source in each router
# A single module import avoids circular imports and ensures both
# references point to the exact same object.
#
# Usage in routers:
#   from app.core.limiter import limiter
#
#   @router.post("/token")
#   @limiter.limit("10/minute")
#   async def login(request: Request, ...):   # <-- Request MUST be first arg

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],   # global safety net
)
