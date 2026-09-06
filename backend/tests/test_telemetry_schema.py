"""2단계 완료 기준 검증: TelemetryFrame이 정상 프레임을 통과시키고 잘못된 프레임을 거부하는지."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.telemetry import FlightMode, TelemetryFrame


def _valid_kwargs(**overrides) -> dict:
    kwargs = {
        "asset_id": "drone-01",
        "event_time": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "sequence_no": 0,
        "latitude": 37.5,
        "longitude": 127.0,
        "altitude_m": 100.0,
        "battery_pct": 95.0,
        "flight_mode": FlightMode.AUTO,
    }
    kwargs.update(overrides)
    return kwargs


def test_valid_frame_passes():
    frame = TelemetryFrame(**_valid_kwargs())
    assert frame.asset_id == "drone-01"
    assert frame.schema_version == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"latitude": 91.0},
        {"latitude": -91.0},
        {"longitude": 181.0},
        {"battery_pct": -1.0},
        {"battery_pct": 101.0},
        {"roll_deg": 200.0},
        {"pitch_deg": 91.0},
        {"yaw_deg": -181.0},
        {"heading_deg": 360.0},
        {"sequence_no": -1},
        {"asset_id": "   "},
    ],
)
def test_out_of_range_values_rejected(overrides):
    with pytest.raises(ValidationError):
        TelemetryFrame(**_valid_kwargs(**overrides))


def test_received_at_before_event_time_rejected():
    with pytest.raises(ValidationError):
        TelemetryFrame(
            **_valid_kwargs(
                event_time=datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc),
                received_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            )
        )


def test_received_at_after_event_time_accepted():
    frame = TelemetryFrame(
        **_valid_kwargs(
            event_time=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            received_at=datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc),
        )
    )
    assert frame.received_at > frame.event_time
