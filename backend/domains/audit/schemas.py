from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from shared.schemas import _BaseSchema


class AuditLogRead(_BaseSchema):
    id: uuid.UUID
    actor_id: uuid.UUID | None = Field(default=None)
    action: str
    entity_type: str
    entity_id: str
    metadata: dict | None = Field(default=None)
    created_at: datetime
