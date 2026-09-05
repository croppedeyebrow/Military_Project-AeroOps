"""TelemetryFrame 데이터 계약 (스텁).

`docs/planning/05_데이터엔지니어링_아키텍처.md`에 정의된 필드를 2단계에서
구체화한다: schema_version, asset_id, mission_id, event_time, received_at,
sequence_no, 위치, 속도, heading, roll/pitch/yaw, 배터리, RSSI, 비행 모드.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class TelemetryFrame(BaseModel):
    schema_version: int = 1
    asset_id: str
    mission_id: str | None = None
    event_time: datetime
    received_at: datetime | None = None
    sequence_no: int

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_m: float

    speed_mps: float | None = None
    heading_deg: float | None = Field(default=None, ge=0, le=360)
    roll_deg: float | None = None
    pitch_deg: float | None = None
    yaw_deg: float | None = None

    battery_pct: float = Field(ge=0, le=100)
    rssi_dbm: float | None = None
    flight_mode: str | None = None
