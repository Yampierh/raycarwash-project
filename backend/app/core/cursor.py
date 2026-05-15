"""
app/core/cursor.py — Opaque cursor helpers for uniform pagination across /api/v1/*.

A cursor encodes the (created_at, id) of the boundary item between two pages.
Clients treat the cursor string as opaque; the server validates and decodes it.

Usage in a router:
    cursor_data = decode_cursor(cursor) if cursor else None
    stmt = select(Model).where(...)
    if cursor_data:
        stmt = stmt.where(
            tuple_(Model.created_at, Model.id) < (cursor_data["created_at"], cursor_data["id"])
        )
    stmt = stmt.order_by(Model.created_at.desc(), Model.id.desc()).limit(limit + 1)
    items = await session.scalars(stmt).all()
    has_more = len(items) > limit
    items = items[:limit]
    next_cursor = encode_cursor(items[-1]) if items and has_more else None
"""
from __future__ import annotations

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

_MAX_LIMIT = 100
_DEFAULT_LIMIT = 20


def parse_limit(value: int | None, default: int = _DEFAULT_LIMIT, maximum: int = _MAX_LIMIT) -> int:
    """Clamp the limit query param to [1, maximum]."""
    if value is None:
        return default
    if value < 1:
        return 1
    if value > maximum:
        return maximum
    return value


def encode_cursor(item: Any, *, ts_attr: str = "created_at", id_attr: str = "id") -> str:
    """
    Build an opaque cursor string from an ORM-like object or dict.
    Pulls `created_at` (datetime) and `id` (UUID or str) from the item.
    """
    ts = _resolve_attr(item, ts_attr)
    item_id = _resolve_attr(item, id_attr)
    if ts is None or item_id is None:
        raise ValueError(f"encode_cursor: missing {ts_attr} or {id_attr} on item")
    payload = {
        "ts": _normalize_ts(ts),
        "id": str(item_id),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(token: str) -> dict[str, Any]:
    """
    Decode an opaque cursor. Returns `{created_at: datetime, id: UUID|str}`.
    Raises HTTPException 400 on malformed input — safer than letting it bubble.
    """
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty cursor")
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        created_at = datetime.fromisoformat(payload["ts"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        item_id = payload["id"]
        try:
            item_id = UUID(item_id)
        except (ValueError, AttributeError, TypeError):
            pass  # leave as string (some IDs are not UUIDs)
        return {"created_at": created_at, "id": item_id}
    except Exception as exc:
        logger.debug("decode_cursor failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid cursor")


def _resolve_attr(item: Any, name: str) -> Any:
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _normalize_ts(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat()
