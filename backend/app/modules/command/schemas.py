"""Command API 응답 모델."""
from datetime import datetime

from pydantic import BaseModel


class CommandCreatedResponse(BaseModel):
    command_id: str
    idempotency_key: str
    target_asset_id: str
    command_type: str
    status: str
    created_at: datetime
    is_new: bool  # False면 기존 명령을 멱등하게 반환한 것(재실행이 아니다).
