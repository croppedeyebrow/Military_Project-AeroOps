"""기체 측 Command ACK·실행결과·last_processed_command_id 시뮬레이션 검증."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from simulator.command_handler import DeviceCommandHandler
from simulator.contracts.command import CommandEnvelope

ISSUED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
EXPIRES_AT = ISSUED_AT + timedelta(minutes=5)


def _command(**overrides) -> CommandEnvelope:
    kwargs = {
        "command_id": "cmd-0001",
        "idempotency_key": "op-console-0001",
        "target_asset_id": "drone-01",
        "command_type": "RTL",
        "requested_by": "operator-1",
        "issued_at": ISSUED_AT,
        "expires_at": EXPIRES_AT,
    }
    kwargs.update(overrides)
    return CommandEnvelope(**kwargs)


def _handler(failure_rate: float = 0.0, seed: int = 1) -> DeviceCommandHandler:
    return DeviceCommandHandler(
        asset_id="drone-01", rng=np.random.default_rng(seed), failure_rate=failure_rate
    )


def test_acknowledge_returns_command_and_asset_id():
    handler = _handler()
    ack = handler.acknowledge(_command(), now=ISSUED_AT)
    assert ack.command_id == "cmd-0001"
    assert ack.asset_id == "drone-01"
    assert ack.acknowledged_at == ISSUED_AT


def test_process_before_expiry_succeeds_when_failure_rate_zero():
    handler = _handler(failure_rate=0.0)
    result = handler.process(_command(), now=ISSUED_AT + timedelta(seconds=1))
    assert result.status == "SUCCEEDED"
    assert handler.last_processed_command_id == "cmd-0001"


def test_process_before_expiry_fails_when_failure_rate_one():
    handler = _handler(failure_rate=1.0)
    result = handler.process(_command(), now=ISSUED_AT + timedelta(seconds=1))
    assert result.status == "FAILED"
    assert result.detail is not None


def test_process_after_expiry_times_out_regardless_of_failure_rate():
    handler = _handler(failure_rate=0.0)  # 성공률 100%라도 만료면 TIMED_OUT이어야 한다
    result = handler.process(_command(), now=EXPIRES_AT + timedelta(seconds=1))
    assert result.status == "TIMED_OUT"
    assert handler.last_processed_command_id == "cmd-0001"


def test_last_processed_command_id_tracks_most_recent():
    handler = _handler()
    handler.process(_command(command_id="cmd-0001"), now=ISSUED_AT)
    handler.process(_command(command_id="cmd-0002"), now=ISSUED_AT)
    assert handler.last_processed_command_id == "cmd-0002"


def test_same_seed_produces_same_outcome_sequence():
    commands = [_command(command_id=f"cmd-{i:04d}") for i in range(20)]

    handler_a = _handler(failure_rate=0.5, seed=7)
    handler_b = _handler(failure_rate=0.5, seed=7)

    outcomes_a = [handler_a.process(c, now=ISSUED_AT).status for c in commands]
    outcomes_b = [handler_b.process(c, now=ISSUED_AT).status for c in commands]

    assert outcomes_a == outcomes_b
    assert "FAILED" in outcomes_a and "SUCCEEDED" in outcomes_a  # 둘 다 나와야 의미있는 테스트


@pytest.mark.parametrize("bad_expires_at", [ISSUED_AT, ISSUED_AT - timedelta(seconds=1)])
def test_command_fixture_itself_rejects_non_future_expiry(bad_expires_at):
    with pytest.raises(Exception):  # noqa: B017 — CommandEnvelope의 pydantic ValidationError
        _command(expires_at=bad_expires_at)
