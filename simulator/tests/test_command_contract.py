"""시뮬레이터 측 CommandEnvelope 계약이 backend와 동일하게 정상/오류를 판별하는지 검증한다."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from simulator.contracts.command import CommandEnvelope
from simulator.contracts.telemetry import TelemetryFrame


def _valid_kwargs(**overrides) -> dict:
    kwargs = {
        "command_id": "cmd-0001",
        "idempotency_key": "op-console-0001",
        "target_asset_id": "drone-01",
        "command_type": "RTL",
        "requested_by": "operator-1",
        "issued_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "expires_at": datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
    }
    kwargs.update(overrides)
    return kwargs


def test_valid_command_passes():
    command = CommandEnvelope(**_valid_kwargs())
    assert command.schema_version == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"command_id": ""},
        {"idempotency_key": "  "},
        {"expected_asset_state_version": -5},
    ],
)
def test_invalid_fields_rejected(overrides):
    with pytest.raises(ValidationError):
        CommandEnvelope(**_valid_kwargs(**overrides))


def test_expires_before_issued_rejected():
    with pytest.raises(ValidationError):
        CommandEnvelope(
            **_valid_kwargs(
                issued_at=datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
                expires_at=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            )
        )


def test_telemetry_shaped_payload_rejected_as_command():
    telemetry_shaped = {
        "asset_id": "drone-01",
        "event_time": "2026-01-01T00:00:00Z",
        "sequence_no": 0,
        "latitude": 37.5,
        "longitude": 127.0,
        "altitude_m": 100.0,
        "battery_pct": 90.0,
    }
    with pytest.raises(ValidationError):
        CommandEnvelope(**telemetry_shaped)


def test_command_shaped_payload_rejected_as_telemetry():
    with pytest.raises(ValidationError):
        TelemetryFrame(**_valid_kwargs())
