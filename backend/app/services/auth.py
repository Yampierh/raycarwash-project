# COMPATIBILITY SHIM
from domains.auth.service import (  # noqa: F401
    AuthService,
    get_current_user,
    get_current_user_for_onboarding,
    ws_get_current_user,
    require_role,
)
