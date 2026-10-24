"""TelemetryFrame 데이터 계약.

`docs/planning/05_데이터엔지니어링_아키텍처.md`와
`docs/api/telemetry_frame_dictionary.md`에 정의된 필드·단위·축·범위를 따른다.

좌표계 요약 (자세한 내용은 데이터 사전 참고):
- 위치: WGS84 경위도(도), 고도는 지면 기준 m
- heading_deg: 지면 진행 방향(ground track), 0=N, 90=E, 시계방향, [0, 360)
- yaw_deg: 기체 기수 방향(body heading), heading과 별개 정의, [-180, 180]
- roll_deg: 우측으로 기울면 양수, [-180, 180]
- pitch_deg: 기수가 위로 들리면 양수, [-90, 90]
"""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class FlightMode(str, Enum):
    """`docs/api/telemetry_frame_dictionary.md`에 정의된 비행 모드."""

    MANUAL = "MANUAL"
    AUTO = "AUTO"
    GUIDED = "GUIDED"
    LOITER = "LOITER"
    RTL = "RTL"  # Return To Launch
    LANDED = "LANDED"


class TelemetryFrame(BaseModel):
    schema_version: int = 1
    asset_id: str = Field(min_length=1)
    mission_id: str | None = None
    event_time: datetime
    received_at: datetime | None = None
    sequence_no: int = Field(ge=0)

    # 추적성 필드(`docs/planning/03_데이터베이스_아키텍처.md` "이벤트·배포 추적성").
    # 7단계(이벤트 재생·배포 추적)에서 실제 값이 채워지기 전까지는 선택값으로 둔다.
    operation_session_id: str | None = None
    deployment_id: str | None = None
    correlation_id: str | None = None

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
        """서버 수신 시각은 원본 이벤트 시각보다 앞설 수 없다(시계 오차 허용치는 두지 않는다).

        지연(delay) 장애 시나리오는 이 관계를 유지한 채 두 시각의 차이를 키우는
        방식으로 표현한다. 참고: `docs/planning/02_백엔드_아키텍처.md`의
        "원본 이벤트 시각과 서버 수신 시각을 모두 저장한다".
        """
        if self.received_at is not None and self.received_at < self.event_time:
            raise ValueError("received_at은 event_time보다 이전일 수 없다")
        return self
