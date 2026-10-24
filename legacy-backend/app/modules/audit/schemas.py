"""Audit 조회 응답 모델."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    actor: str
    action: str
    target_type: str
    target_id: str
    result: str
    detail: dict[str, Any] | None
    occurred_at: datetime

    model_config = {"from_attributes": True}
