"""
domains/users/include_spec.py — Parser for the Profile Hub `?include=` query
parameter (ADR-002b §2.2.1).

Responsibilities:
  - Validate the comma-separated token list against a fixed whitelist.
  - Drop tokens that don't apply to the caller's roles (e.g. `provider` for
    a pure client) silently — this avoids 4xx errors on role-switch races
    on the frontend.
  - Identify the subset that requires step-up auth so the router can branch
    early on `?on_step_up=skip`.

The parser is pure: no DB access, no FastAPI types. The router instantiates
it with the current user's roles.

Unknown tokens raise `BadIncludeToken`. The exception handlers (Phase 0)
translate it into 400 `bad_request` with the list of valid tokens in
`details`.
"""
from __future__ import annotations

from dataclasses import dataclass

# ─── Whitelist ────────────────────────────────────────────────────────────────

# Tokens valid in any role.
_UNIVERSAL_TOKENS: frozenset[str] = frozenset({
    "profile",
    "stats",
    "addresses",
    "payment_methods",
    "notifications",
    "security",
    "sessions",
})

# Tokens that require `client` role.
_CLIENT_TOKENS: frozenset[str] = frozenset({
    "vehicles",
    "favorites",
    "preferences",
})

# Tokens that require `detailer` role.
_DETAILER_TOKENS: frozenset[str] = frozenset({
    "provider",
})

# Tokens that require recent step-up auth (ADR-002b §2.2.4).
SENSITIVE_TOKENS: frozenset[str] = frozenset({
    "security",
    "sessions",
})

ALL_TOKENS: frozenset[str] = _UNIVERSAL_TOKENS | _CLIENT_TOKENS | _DETAILER_TOKENS


class BadIncludeToken(ValueError):
    """Raised when `?include=` contains a token outside the whitelist."""

    def __init__(self, token: str) -> None:
        super().__init__(f"unknown include token: {token!r}")
        self.token = token


@dataclass(frozen=True)
class IncludeSpec:
    """
    The set of blocks the caller asked for, filtered against their roles.

    Attributes:
        requested:           tokens the caller actually typed in ?include=
        effective:           tokens that will be populated in the response
        skipped_for_role:    tokens dropped because the caller's role
                             doesn't grant them (e.g. `provider` for a
                             pure client). These are silently dropped, not
                             rejected, so frontend role-switch races don't
                             break.
        sensitive:           subset of `effective` that requires step-up.
    """
    requested: frozenset[str]
    effective: frozenset[str]
    skipped_for_role: frozenset[str]
    sensitive: frozenset[str]

    def has(self, token: str) -> bool:
        return token in self.effective

    @classmethod
    def parse(cls, raw: str | None, *, roles: set[str]) -> "IncludeSpec":
        """
        Build an `IncludeSpec` from the raw query value and the caller's roles.

        Behavior matches ADR-002b §2.2:
        - Empty / None → empty `requested` (only `user` + `verification_badges`
          will be in the response).
        - Tokens are case-sensitive, whitespace-trimmed, deduplicated.
        - Unknown tokens raise `BadIncludeToken`.
        - Role-mismatched tokens go into `skipped_for_role`, not `effective`.
        """
        if not raw:
            return cls(
                requested=frozenset(),
                effective=frozenset(),
                skipped_for_role=frozenset(),
                sensitive=frozenset(),
            )

        requested: set[str] = set()
        for part in raw.split(","):
            tok = part.strip()
            if not tok:
                continue
            if tok not in ALL_TOKENS:
                raise BadIncludeToken(tok)
            requested.add(tok)

        effective: set[str] = set()
        skipped: set[str] = set()
        for tok in requested:
            if tok in _UNIVERSAL_TOKENS:
                effective.add(tok)
            elif tok in _CLIENT_TOKENS and "client" in roles:
                effective.add(tok)
            elif tok in _DETAILER_TOKENS and ("detailer" in roles or "admin" in roles):
                effective.add(tok)
            else:
                skipped.add(tok)

        return cls(
            requested=frozenset(requested),
            effective=frozenset(effective),
            skipped_for_role=frozenset(skipped),
            sensitive=frozenset(effective & SENSITIVE_TOKENS),
        )
