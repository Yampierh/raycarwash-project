"""
infrastructure/auth/device_parser.py — minimal User-Agent → device label.

Plan 23 Fase 2 día 1. Lightweight regex-based parser to populate
`sessions.device_name` and `sessions.device_type` from the request's
User-Agent header. No third-party deps — keeps the auth path zero-cost.

Catches the common cases:
  - iPhone, iPad, Android phone/tablet, Mac, Windows, Linux
  - Safari / Chrome / Firefox / Edge

Anything we don't recognize falls back to a generic `"api"` device_type
and `None` for device_name (caller can show "Unknown device").
"""
from __future__ import annotations

import re


_DEVICE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("iPad",     re.compile(r"\biPad\b", re.IGNORECASE)),
    ("iPhone",   re.compile(r"\biPhone\b", re.IGNORECASE)),
    ("Android",  re.compile(r"\bAndroid\b", re.IGNORECASE)),
    ("Mac",      re.compile(r"\bMac OS X\b|\bMacintosh\b", re.IGNORECASE)),
    ("Windows",  re.compile(r"\bWindows\b", re.IGNORECASE)),
    ("Linux",    re.compile(r"\bLinux\b|\bUbuntu\b", re.IGNORECASE)),
]

_BROWSER_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Order matters — Edge contains "Chrome", Chrome contains "Safari", etc.
    ("Edge",    re.compile(r"\bEdg(?:e|A|iOS)?/[\d.]+", re.IGNORECASE)),
    ("Firefox", re.compile(r"\bFirefox/[\d.]+", re.IGNORECASE)),
    ("Chrome",  re.compile(r"\bChrome/[\d.]+", re.IGNORECASE)),
    ("Safari",  re.compile(r"\bSafari/[\d.]+", re.IGNORECASE)),
    ("curl",    re.compile(r"\bcurl/[\d.]+", re.IGNORECASE)),
    ("httpx",   re.compile(r"\bpython-httpx/[\d.]+", re.IGNORECASE)),
]

_TABLET_HINT = re.compile(r"\b(?:iPad|Tablet|Tab)\b", re.IGNORECASE)
_MOBILE_HINT = re.compile(r"\b(?:Mobile|iPhone|Android.*Mobile)\b", re.IGNORECASE)
_DESKTOP_HINT = re.compile(r"\b(?:Macintosh|Windows NT|X11)\b", re.IGNORECASE)


def parse_device_name(user_agent: str | None) -> str | None:
    """Return a short human-readable label like "iPhone · Safari" or
    "Windows · Chrome". None if no signals found."""
    if not user_agent:
        return None
    parts: list[str] = []
    for label, pat in _DEVICE_PATTERNS:
        if pat.search(user_agent):
            parts.append(label)
            break
    for label, pat in _BROWSER_PATTERNS:
        if pat.search(user_agent):
            parts.append(label)
            break
    if not parts:
        return None
    return " · ".join(parts)


def parse_device_type(user_agent: str | None) -> str:
    """One of: mobile | tablet | desktop | api."""
    if not user_agent:
        return "api"
    if _TABLET_HINT.search(user_agent):
        return "tablet"
    if _MOBILE_HINT.search(user_agent):
        return "mobile"
    if _DESKTOP_HINT.search(user_agent):
        return "desktop"
    return "api"
