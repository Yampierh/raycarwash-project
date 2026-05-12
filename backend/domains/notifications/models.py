from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.db.base import Base


class DevicePlatform(str, enum.Enum):
    IOS     = "ios"
    ANDROID = "android"
    WEB     = "web"


class DeviceToken(Base):
    __tablename__ = "device_tokens"
    __table_args__ = (
        UniqueConstraint("token", name="uq_device_tokens_token"),
        Index("ix_device_tokens_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(512), nullable=False)
    platform: Mapped[DevicePlatform] = mapped_column(
        Enum(DevicePlatform, name="device_platform_enum"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped[User] = relationship("User", lazy="select")

    def __repr__(self) -> str:
        return f"<DeviceToken user={self.user_id} platform={self.platform}>"


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from domains.users.models import User
