"""시뮬레이터 측 TelemetryFrame 계약이 backend와 동일하게 정상/오류를 판별하는지 검증한다."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from simulator.contracts.telemetry import FlightMode, TelemetryFrame


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
    assert frame.schema_version == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"latitude": 91.0},
        {"longitude": -181.0},
        {"battery_pct": 150.0},
        {"roll_deg": -200.0},
        {"pitch_deg": 95.0},
        {"sequence_no": -5},
    ],
)
def test_out_of_range_values_rejected(overrides):
    with pytest.raises(ValidationError):
        TelemetryFrame(**_valid_kwargs(**overrides))
