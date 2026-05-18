"""
domains/providers/portfolio_photo.py — ProviderPortfolioPhoto model
(Phase 5 chunk Y1).

Public-bucket gallery surfaced on the public provider profile and on
the provider's own ProviderHub screen. Max 30 photos per provider
enforced at the service layer.

Keyed on `provider_user_id` (the User.id of the detailer) rather than
ProviderProfile.id so the column lines up with the rest of the
provider surface — favorites / location / verification all join on
user_id, so portfolios match.

Tags are free-form String — "before", "after", "hero" are conventional
but detailers can group however they want ("ceramic_coating",
"interior_detail") without a schema change.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base


class ProviderPortfolioPhoto(Base):
    __tablename__ = "provider_portfolio_photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    s3_key: Mapped[str] = mapped_column(String(255), nullable=False)
    caption: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    provider: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="portfolio_photos",
    )

    def __repr__(self) -> str:
        return f"<ProviderPortfolioPhoto id={self.id} provider={self.provider_user_id}>"


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from domains.users.models import User  # noqa: F401
