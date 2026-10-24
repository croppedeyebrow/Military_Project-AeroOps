"""Alert API 요청/응답 모델."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AcknowledgeAlertRequest(BaseModel):
    acknowledged_by: str = Field(min_length=1)


class ResolveAlertRequest(BaseModel):
    resolved_by: str = Field(min_length=1)


class AlertOut(BaseModel):
    id: int
    asset_id: str
    alert_type: str
    severity: str
    rule_version: str
    evidence: dict[str, Any]
    status: str
    triggered_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None
    resolved_by: str | None

    model_config = {"from_attributes": True}
