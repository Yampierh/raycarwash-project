# domains/auth/service.py — re-exports from app layer (to be migrated)
from app.services.auth import (  # noqa: F401
    AuthService, get_current_user, ws_get_current_user,
    authenticate_user, get_current_user_optional,
)
