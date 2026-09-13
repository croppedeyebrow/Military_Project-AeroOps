"""조회 응답 모델. DB 레코드를 `TelemetryFrame` 계약 형태로 변환한다."""
from __future__ import annotations

from pydantic import BaseModel

from app.modules.telemetry.models import AssetLatestState, TelemetryFrameRecord
from app.schemas.telemetry import FlightMode, TelemetryFrame


def _flight_mode(value: str | None) -> FlightMode | None:
    return FlightMode(value) if value else None


def frame_from_record(record: TelemetryFrameRecord | AssetLatestState) -> TelemetryFrame:
    """DB 레코드(원본 또는 최신 상태)를 응답용 `TelemetryFrame`으로 변환한다."""
    return TelemetryFrame(
        asset_id=record.asset_id,
        mission_id=record.mission_id,
        event_time=record.event_time,
        received_at=record.received_at,
        sequence_no=record.sequence_no,
        latitude=record.latitude,
        longitude=record.longitude,
        altitude_m=record.altitude_m,
        speed_mps=record.speed_mps,
        heading_deg=record.heading_deg,
        roll_deg=record.roll_deg,
        pitch_deg=record.pitch_deg,
        yaw_deg=record.yaw_deg,
        battery_pct=record.battery_pct,
        rssi_dbm=record.rssi_dbm,
        flight_mode=_flight_mode(record.flight_mode),
    )


class TelemetryHistoryResponse(BaseModel):
    asset_id: str
    limit: int
    offset: int
    count: int
    items: list[TelemetryFrame]
