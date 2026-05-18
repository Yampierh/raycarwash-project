"""
domains/providers/achievement.py — ProviderAchievement model
(Phase 5 chunk Y1).

Badges granted to detailers — auto-evaluated daily by the
achievement_evaluator worker (Phase 5 chunk Y6) or manually
inserted by admins. The (provider_user_id, achievement_type)
UNIQUE keeps grants idempotent; re-running the worker for a
detailer that already earned the badge is a no-op.

`achievement_type` is a String (not enum) so adding "ceramic_specialist"
or "fleet_pro" doesn't require a migration. The frontend's badge
catalog renders unknown types as a generic medal icon.

`metadata_` JSONB captures whatever the evaluator wants to remember
at grant time (e.g., the job count that triggered "100 jobs done").
The badge UI can render that without joining other tables.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base


class ProviderAchievement(Base):
    __tablename__ = "provider_achievements"
    __table_args__ = (
        UniqueConstraint(
            "provider_user_id", "achievement_type",
            name="uq_provider_achievements_provider_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    provider_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    achievement_type: Mapped[str] = mapped_column(String(60), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )

    provider: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User", back_populates="achievements",
    )

    def __repr__(self) -> str:
        return (
            f"<ProviderAchievement provider={self.provider_user_id} "
            f"type={self.achievement_type}>"
        )


from typing import TYPE_CHECKING  # noqa: E402
if TYPE_CHECKING:
    from domains.users.models import User  # noqa: F401
