"""TelemetryFrame 계약 (시뮬레이터 측 구현).

`backend/app/schemas/telemetry.py`와 동일한 계약을 독립적으로 구현한다.
동기화 방식은 `docs/decisions/0002-telemetry-contract-duplication.md`,
필드 정의는 `docs/api/telemetry_frame_dictionary.md` 참고.
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class FlightMode(str, Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"
    GUIDED = "GUIDED"
    LOITER = "LOITER"
    RTL = "RTL"
    LANDED = "LANDED"


class TelemetryFrame(BaseModel):
    schema_version: int = 1
    asset_id: str = Field(min_length=1)
    mission_id: str | None = None
    event_time: datetime
    received_at: datetime | None = None
    sequence_no: int = Field(ge=0)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_m: float = Field(ge=-500, le=10000)

    speed_mps: float | None = Field(default=None, ge=0, le=150)
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    roll_deg: float | None = Field(default=None, ge=-180, le=180)
    pitch_deg: float | None = Field(default=None, ge=-90, le=90)
    yaw_deg: float | None = Field(default=None, ge=-180, le=180)

    battery_pct: float = Field(ge=0, le=100)
    rssi_dbm: float | None = Field(default=None, ge=-130, le=0)
    flight_mode: FlightMode | None = None

    @field_validator("asset_id")
    @classmethod
    def asset_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("asset_id는 공백일 수 없다")
        return value

    @model_validator(mode="after")
    def received_at_not_before_event_time(self) -> "TelemetryFrame":
        if self.received_at is not None and self.received_at < self.event_time:
            raise ValueError("received_at은 event_time보다 이전일 수 없다")
        return self
