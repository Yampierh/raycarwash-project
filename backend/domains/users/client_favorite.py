"""
domains/users/client_favorite.py — ClientFavorite model.

Backs the `favorites` block of the Profile Hub. A client can pin
providers they've worked with so the Hub can surface them as quick
re-book options and `stats.favorite_provider_id` (denormalized follow-up
in Phase 9) can be picked without scanning appointments.

Idempotent — `(user_id, provider_user_id)` is UNIQUE, so re-favoring is a
no-op rather than a duplicate row.

Migration: m_008.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base


class ClientFavorite(Base):
    __tablename__ = "client_favorites"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "provider_user_id",
            name="uq_client_favorites_pair",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    # Resolve both sides explicitly — both FKs point at users.id.
    user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[user_id], back_populates="favorites",
    )
    provider: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", foreign_keys=[provider_user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<ClientFavorite user_id={self.user_id} "
            f"provider_user_id={self.provider_user_id}>"
        )


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from domains.users.models import User  # noqa: F401
