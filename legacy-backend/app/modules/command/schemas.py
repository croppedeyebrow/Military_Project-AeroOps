"""Command API 요청/응답 모델."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class CommandCreatedResponse(BaseModel):
    command_id: str
    idempotency_key: str
    target_asset_id: str
    command_type: str
    status: str
    created_at: datetime
    is_new: bool  # False면 기존 명령을 멱등하게 반환한 것(재실행이 아니다).


class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1)


class CancelRequest(BaseModel):
    cancelled_by: str = Field(min_length=1)
    reason: str | None = None


class ResultRequest(BaseModel):
    outcome: Literal["SUCCEEDED", "FAILED"]
    detail: dict[str, Any] | None = None


class CommandStatusResponse(BaseModel):
    command_id: str
    status: str
    updated_at: datetime


class CommandEventOut(BaseModel):
    event_no: int
    event_type: str
    occurred_at: datetime
    actor: str | None
    detail: dict[str, Any] | None

    model_config = {"from_attributes": True}


class CommandDetailResponse(BaseModel):
    command_id: str
    idempotency_key: str
    target_asset_id: str
    command_type: str
    requested_by: str
    approved_by: str | None
    status: str
    issued_at: datetime
    expires_at: datetime
    deployment_id: str | None
    created_at: datetime
    updated_at: datetime
    events: list[CommandEventOut]
