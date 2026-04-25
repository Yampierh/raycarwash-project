from __future__ import annotations

import base64
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings


def _get_encryption_key() -> bytes:
    """Returns ENCRYPTION_KEY as bytes. Separate from JWT_SECRET_KEY."""
    return base64.b64decode(get_settings().ENCRYPTION_KEY)


class Base(AsyncAttrs, DeclarativeBase):
    """Shared declarative base for all domain models."""
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
