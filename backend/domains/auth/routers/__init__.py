"""
domains/auth/routers/__init__.py

Assembles all auth sub-routers into a single auth_router.

Sub-routers by concern:
  core.py             — register, login, logout, token, refresh, me, update,
                        check-email, identify, verify, complete-profile
  social.py           — /auth/google, /auth/apple
  webauthn.py         — /auth/webauthn/* (passkey registration + authentication + CRUD)
  sessions.py         — /auth/sessions (list / revoke)
  password.py         — /auth/password-reset, /auth/password-reset/confirm
  email_verification.py — /auth/email/verify, /auth/email/resend-verification
"""
from fastapi import APIRouter

from .core import router as _core
from .social import router as _social
from .webauthn import router as _webauthn
from .sessions import router as _sessions
from .password import router as _password
from .email_verification import router as _email

auth_router = APIRouter()
auth_router.include_router(_core)
auth_router.include_router(_social)
auth_router.include_router(_webauthn)
auth_router.include_router(_sessions)
auth_router.include_router(_password)
auth_router.include_router(_email)
