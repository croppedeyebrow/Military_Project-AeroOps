"""기체측 실시간 명령 반응(`device_loop.py`) 검증.

`apply_command`/`advance_pose`/`flight_mode_for`/`extract_payload`는 순수 함수라
HTTP 없이 바로 테스트한다. `poll_and_apply_commands`/`report_completed_commands`는
실제 `DeviceCommandClient` 대신 호출 기록만 남기는 가짜 클라이언트(덕 타이핑 — 두
함수 모두 isinstance를 확인하지 않고 메서드만 호출한다)로 ACK/EXECUTE/RESULT 순서와
기체 상태 전이를 확인한다.
"""
from __future__ import annotations

import numpy as np
import pytest

from simulator.contracts.telemetry import FlightMode
from simulator.device_loop import (
    DroneRuntimeState,
    advance_pose,
    apply_command,
    extract_payload,
    flight_mode_for,
    poll_and_apply_commands,
    report_completed_commands,
)
from simulator.generator import BASE_LAT, BASE_LON, DroneConfig
from simulator.scenarios import CircleScenario


def _drone(asset_id: str = "drone-01") -> DroneConfig:
    scenario = CircleScenario(
        center_lat=BASE_LAT, center_lon=BASE_LON, altitude_m=100.0, radius_m=300.0, speed_mps=12.0
    )
    return DroneConfig(
        asset_id=asset_id, scenario=scenario, start_battery_pct=95.0, rng=np.random.default_rng(1)
    )


def _state(**overrides) -> DroneRuntimeState:
    base = {"config": _drone(), "lat": BASE_LAT, "lon": BASE_LON, "alt": 100.0}
    base.update(overrides)
    return DroneRuntimeState(**base)


class FakeCommandClient:
    """`DeviceCommandClient`와 같은 메서드만 흉내내는 테스트용 가짜."""

    def __init__(self, dispatched: list[dict], details: dict[str, dict]):
        self._dispatched = dispatched
        self._details = details
        self.calls: list[tuple] = []

    def list_dispatched(self):
        return self._dispatched

    def get_detail(self, command_id: str):
        return self._details.get(command_id)

    def ack(self, command_id: str) -> bool:
        self.calls.append(("ack", command_id))
        return True

    def execute(self, command_id: str) -> bool:
        self.calls.append(("execute", command_id))
        return True

    def result(self, command_id: str, outcome: str, detail) -> bool:
        self.calls.append(("result", command_id, outcome))
        return True


def _detail(command_id: str, asset_id: str, command_type: str, payload: dict) -> dict:
    return {
        "command_id": command_id,
        "target_asset_id": asset_id,
        "command_type": command_type,
        "events": [{"event_type": "CREATED", "detail": {"payload": payload}}],
    }


class TestApplyCommand:
    def test_rtl_sets_returning_mode_toward_base(self):
        state = _state(lat=BASE_LAT + 0.05, lon=BASE_LON + 0.05, alt=120.0)
        accepted, reason = apply_command(state, "RTL", {})
        assert accepted is True
        assert reason is None
        assert state.mode == "RETURNING"
        assert state.target_lat == BASE_LAT
        assert state.target_lon == BASE_LON

    def test_move_to_requires_lat_lon(self):
        state = _state()
        accepted, reason = apply_command(state, "MOVE_TO", {})
        assert accepted is False
        assert reason is not None

    def test_move_to_with_valid_payload(self):
        state = _state()
        accepted, _ = apply_command(
            state, "MOVE_TO", {"target_latitude": 37.4, "target_longitude": 127.2, "target_altitude_m": 80}
        )
        assert accepted is True
        assert state.mode == "MOVING_TO"
        assert state.target_lat == 37.4
        assert state.target_alt == 80

    def test_loiter_holds_current_position(self):
        state = _state(lat=37.41, lon=127.05, alt=90.0)
        accepted, _ = apply_command(state, "LOITER", {})
        assert accepted is True
        assert state.mode == "LOITERING"
        assert (state.target_lat, state.target_lon, state.target_alt) == (37.41, 127.05, 90.0)

    def test_arm_disarm_toggle_armed_flag(self):
        state = _state(armed=False)
        apply_command(state, "ARM", {})
        assert state.armed is True
        apply_command(state, "DISARM", {})
        assert state.armed is False

    def test_set_altitude_rejected_while_still_in_scenario_mode(self):
        state = _state()  # mode defaults to SCENARIO
        accepted, reason = apply_command(state, "SET_ALTITUDE", {"target_altitude_m": 50})
        assert accepted is False
        assert "SCENARIO" in reason

    def test_set_altitude_accepted_once_loitering(self):
        state = _state(mode="LOITERING")
        accepted, _ = apply_command(state, "SET_ALTITUDE", {"target_altitude_m": 50})
        assert accepted is True
        assert state.target_alt == 50

    def test_set_speed_updates_transit_speed(self):
        state = _state()
        accepted, _ = apply_command(state, "SET_SPEED", {"target_speed_mps": 20})
        assert accepted is True
        assert state.transit_speed_mps == 20

    def test_unknown_command_type_rejected(self):
        accepted, reason = apply_command(_state(), "SELF_DESTRUCT", {})
        assert accepted is False
        assert reason is not None


class TestAdvancePose:
    def test_scenario_mode_delegates_to_scenario_pose_at(self):
        state = _state()
        pose = advance_pose(state, t=5.0, dt=1.0)
        expected = state.config.scenario.pose_at(5.0)
        assert pose.latitude == expected.latitude
        assert state.lat == expected.latitude

    def test_disarmed_freezes_in_place(self):
        state = _state(lat=37.4, lon=127.1, alt=100.0, mode="LOITERING", armed=False)
        pose = advance_pose(state, t=10.0, dt=1.0)
        assert pose.latitude == 37.4
        assert pose.longitude == 127.1
        assert pose.speed_mps == 0.0

    def test_returning_moves_toward_base_and_arrives(self):
        # 목표(BASE_LAT/LON)에서 아주 가까운 곳에서 시작 — 한 틱 안에 도착해야 한다.
        state = _state(lat=BASE_LAT + 0.00001, lon=BASE_LON, alt=30.0, mode="RETURNING")
        state.target_lat, state.target_lon, state.target_alt = BASE_LAT, BASE_LON, 30.0
        pose = advance_pose(state, t=0.0, dt=1.0)
        assert pose.latitude == pytest.approx(BASE_LAT, abs=1e-6)
        assert state.mode == "LOITERING"  # 도착 후 대기 모드로 전환

    def test_returning_steps_toward_target_without_overshooting_when_far(self):
        state = _state(lat=BASE_LAT + 1.0, lon=BASE_LON, alt=30.0, mode="RETURNING")
        state.target_lat, state.target_lon, state.target_alt = BASE_LAT, BASE_LON, 30.0
        advance_pose(state, t=0.0, dt=1.0)
        assert state.mode == "RETURNING"  # 아직 멀어서 도착 못 함
        assert state.lat < BASE_LAT + 1.0  # 그래도 목표 쪽으로는 움직임

    def test_loitering_holds_lat_lon_but_eases_altitude_toward_target(self):
        state = _state(lat=37.4, lon=127.1, alt=100.0, mode="LOITERING", target_alt=50.0)
        pose = advance_pose(state, t=0.0, dt=1.0)
        assert pose.latitude == 37.4
        assert pose.altitude_m < 100.0  # 목표(50)쪽으로 한 틱만큼 내려감
        assert pose.speed_mps == 0.0


class TestFlightModeFor:
    def test_maps_each_mode_to_expected_flight_mode(self):
        assert flight_mode_for(_state(mode="SCENARIO")) == FlightMode.AUTO
        assert flight_mode_for(_state(mode="RETURNING")) == FlightMode.RTL
        assert flight_mode_for(_state(mode="MOVING_TO")) == FlightMode.GUIDED
        assert flight_mode_for(_state(mode="LOITERING")) == FlightMode.LOITER

    def test_disarmed_overrides_mode_to_manual(self):
        assert flight_mode_for(_state(mode="RETURNING", armed=False)) == FlightMode.MANUAL


class TestExtractPayload:
    def test_finds_payload_in_created_event(self):
        detail = _detail("cmd-1", "drone-01", "MOVE_TO", {"target_latitude": 1.0})
        assert extract_payload(detail) == {"target_latitude": 1.0}

    def test_returns_empty_dict_when_no_created_event(self):
        assert extract_payload({"events": []}) == {}


class TestPollAndApplyCommands:
    def test_acks_executes_and_applies_to_matching_drone(self):
        states = {"drone-01": _state()}
        client = FakeCommandClient(
            dispatched=[{"command_id": "cmd-1", "status": "DISPATCHED"}],
            details={"cmd-1": _detail("cmd-1", "drone-01", "RTL", {})},
        )
        poll_and_apply_commands(client, states)

        assert states["drone-01"].mode == "RETURNING"
        assert states["drone-01"].active_command_id == "cmd-1"
        assert ("ack", "cmd-1") in client.calls
        assert ("execute", "cmd-1") in client.calls
        # RTL은 도착해야 끝나는 명령이라 이 시점엔 아직 result가 보고되지 않는다.
        assert not any(call[0] == "result" for call in client.calls)

    def test_instant_command_reports_success_immediately(self):
        states = {"drone-01": _state()}
        client = FakeCommandClient(
            dispatched=[{"command_id": "cmd-2", "status": "DISPATCHED"}],
            details={"cmd-2": _detail("cmd-2", "drone-01", "LOITER", {})},
        )
        poll_and_apply_commands(client, states)

        assert states["drone-01"].active_command_id is None  # 즉시 끝났으니 다시 "안 바쁨"
        assert ("result", "cmd-2", "SUCCEEDED") in client.calls

    def test_invalid_payload_reports_failure_immediately(self):
        states = {"drone-01": _state()}
        client = FakeCommandClient(
            dispatched=[{"command_id": "cmd-3", "status": "DISPATCHED"}],
            details={"cmd-3": _detail("cmd-3", "drone-01", "MOVE_TO", {})},  # 좌표 없음
        )
        poll_and_apply_commands(client, states)

        assert ("result", "cmd-3", "FAILED") in client.calls
        assert states["drone-01"].active_command_id is None

    def test_busy_drone_ignores_new_dispatched_command(self):
        states = {"drone-01": _state(active_command_id="cmd-already-running")}
        client = FakeCommandClient(
            dispatched=[{"command_id": "cmd-4", "status": "DISPATCHED"}],
            details={"cmd-4": _detail("cmd-4", "drone-01", "RTL", {})},
        )
        poll_and_apply_commands(client, states)

        assert states["drone-01"].active_command_id == "cmd-already-running"  # 안 바뀜
        assert client.calls == []  # 아예 ACK도 안 함

    def test_command_for_unknown_asset_is_ignored(self):
        states = {"drone-01": _state()}
        client = FakeCommandClient(
            dispatched=[{"command_id": "cmd-5", "status": "DISPATCHED"}],
            details={"cmd-5": _detail("cmd-5", "drone-99", "RTL", {})},
        )
        poll_and_apply_commands(client, states)
        assert client.calls == []


class TestReportCompletedCommands:
    def test_reports_success_once_loitering_and_clears_active_command(self):
        states = {"drone-01": _state(mode="LOITERING", active_command_id="cmd-1")}
        client = FakeCommandClient(dispatched=[], details={})
        report_completed_commands(client, states)

        assert ("result", "cmd-1", "SUCCEEDED") in client.calls
        assert states["drone-01"].active_command_id is None

    def test_does_not_report_while_still_en_route(self):
        states = {"drone-01": _state(mode="RETURNING", active_command_id="cmd-1")}
        client = FakeCommandClient(dispatched=[], details={})
        report_completed_commands(client, states)

        assert client.calls == []
        assert states["drone-01"].active_command_id == "cmd-1"
