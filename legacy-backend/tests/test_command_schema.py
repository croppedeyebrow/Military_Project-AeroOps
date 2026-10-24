"""2단계 보정 검증: CommandEnvelope 계약과 Telemetry/Command 채널 분리."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.command import CommandEnvelope
from app.schemas.telemetry import TelemetryFrame


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
    assert command.payload == {}
    assert command.approved_by is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"command_id": "   "},
        {"idempotency_key": ""},
        {"target_asset_id": " "},
        {"command_type": ""},
        {"requested_by": ""},
        {"expected_asset_state_version": -1},
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


def test_expires_equal_to_issued_rejected():
    same = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        CommandEnvelope(**_valid_kwargs(issued_at=same, expires_at=same))


def test_payload_accepts_arbitrary_json_object():
    command = CommandEnvelope(**_valid_kwargs(payload={"altitude_m": 50, "hold_seconds": 30}))
    assert command.payload == {"altitude_m": 50, "hold_seconds": 30}


class TestChannelSeparation:
    """Telemetry/Command 계약은 필드 집합이 겹치지 않아 서로의 데이터를 거부해야 한다."""

    def test_telemetry_shaped_payload_rejected_as_command(self):
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

    def test_command_shaped_payload_rejected_as_telemetry(self):
        command_shaped = _valid_kwargs()
        with pytest.raises(ValidationError):
            TelemetryFrame(**command_shaped)
