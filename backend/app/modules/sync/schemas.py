"""Sync API 요청/응답 모델."""
from pydantic import BaseModel, Field

from app.schemas.telemetry import TelemetryFrame

MAX_LISTED_MISSING_SEQUENCE_NUMBERS = 1000


class SyncRequest(BaseModel):
    """기체가 재연결 시 제출하는 자기 상태 요약."""

    last_sequence_no: int = Field(ge=0, description="기체가 마지막으로 송신했다고 믿는 sequence_no")
    state_version: int | None = None
    last_processed_command_id: str | None = None


class SyncResponse(BaseModel):
    asset_id: str
    server_last_sequence_no: int | None
    sequence_gap_count: int
    missing_sequence_numbers: list[int]  # 최대 MAX_LISTED_MISSING_SEQUENCE_NUMBERS개만 나열
    anomaly: str | None  # 예: "device_behind_server"
    pending_command_ids: list[str]
    snapshot_reissued: bool
    latest_state: TelemetryFrame | None
