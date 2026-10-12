"""기체측 실시간 명령 반응 — 이게 없으면 명령이 `DISPATCHED`에 멈춰 있다가
타임아웃될 뿐, 실제로 드론이 움직이지 않는다(2026-10-12, 사용자가 RTL을 보냈는데
아무 일도 안 일어난다고 보고해서 발견).

`command_handler.py`의 `DeviceCommandHandler`는 "명령을 받으면 ACK/결과를 어떻게
돌려주는가"만 다루는 순수 로직이었고, 실제 HTTP로 명령을 받아오거나 비행 경로를
바꾸는 부분은 없었다 — 이 파일이 그 빠진 부분이다:
1. `GET /commands?status=DISPATCHED`를 매 틱 한 번만 조회(기체별로 따로 조회하지
   않는다 — 10대 기준 요청 수를 10배 줄인다)해서 내 드론에 해당하는 명령을 찾는다.
2. 그 명령을 실제로 "수행"한다 — 비행 모드를 바꾸고, 목적지로 직선 비행하거나
   그 자리에 멈추거나 한다(`advance_pose`).
3. 도착/적용 완료 시점에 ACK→EXECUTING→SUCCEEDED/FAILED를 실제 `/commands/{id}/...`
   endpoint로 보고한다.

기존 사전계산(`generator.generate_frames`) 경로는 그대로 둔다 — 장애 주입
(`--faults`/`--reorder-window`)은 "미리 계산된 전체 시퀀스를 변형"하는 방식이라 이
실시간 반응형 루프와 전제가 다르다(`main.py`에서 faults가 없고 `--real-time`일 때만
이 루프를 쓴다).
"""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import httpx

from simulator.contracts.telemetry import FlightMode, TelemetryFrame
from simulator.generator import BASE_LAT, BASE_LON, DroneConfig
from simulator.scenarios.base import Pose, bearing_deg, horizontal_distance_m, offset_latlon, to_signed_deg

# "본부(HQ)" 좌표 — frontend/src/components/OperationsMap/OperationsMapView.tsx의
# BASE_ORIGIN과 반드시 같은 값을 유지해야 한다. RTL은 바로 이 좌표로 돌아간다.
RTL_ALTITUDE_M = 30.0
ARRIVAL_THRESHOLD_M = 5.0
ALTITUDE_ARRIVAL_THRESHOLD_M = 1.0
ALTITUDE_RATE_MPS = 3.0
DEFAULT_TRANSIT_SPEED_MPS = 15.0

FlightModeState = Literal["SCENARIO", "RETURNING", "MOVING_TO", "LOITERING"]

_MODE_TO_FLIGHT_MODE: dict[FlightModeState, FlightMode] = {
    "SCENARIO": FlightMode.AUTO,
    "RETURNING": FlightMode.RTL,
    "MOVING_TO": FlightMode.GUIDED,
    "LOITERING": FlightMode.LOITER,
}

# 즉시 끝나는(도착 개념이 없는) 명령 — ACK/EXECUTING 직후 바로 결과를 보고한다.
INSTANT_COMMAND_TYPES = {"LOITER", "ARM", "DISARM", "SET_SPEED"}
# 기체가 이미 명령 모드(RTL/MOVE_TO/LOITER로 임무경로를 벗어난 상태)일 때만 의미가
# 있는 명령 — 아직 SCENARIO(사전 계획 경로) 중이면 "바꿀 대상 모드가 없다"는 뜻이라
# 바로 실패시킨다. 임무경로 중 고도/속도만 즉흥적으로 바꾸는 것까지는 이번 범위에
# 넣지 않았다(아래 README "의도적으로 하지 않은 것" 참고).
REQUIRES_ACTIVE_MODE = {"SET_ALTITUDE"}


@dataclass
class DroneRuntimeState:
    """실시간 루프에서만 쓰는 기체 한 대의 가변 상태. `DroneConfig`(seed로 고정된
    시나리오 설정)는 안 바뀌지만, 이건 명령에 따라 매 틱 바뀐다."""

    config: DroneConfig
    lat: float
    lon: float
    alt: float
    mode: FlightModeState = "SCENARIO"
    target_lat: float | None = None
    target_lon: float | None = None
    target_alt: float | None = None
    transit_speed_mps: float = DEFAULT_TRANSIT_SPEED_MPS
    armed: bool = True
    active_command_id: str | None = None
    last_processed_command_id: str | None = None


def _step_altitude(current: float, target: float | None, dt: float) -> float:
    """고도를 `ALTITUDE_RATE_MPS` 속도로 목표치까지 서서히 바꾼다(한 번에 순간이동하지
    않는다 — 수평 이동과 같은 "서서히 다가간다" 원칙)."""
    if target is None:
        return current
    diff = target - current
    if abs(diff) <= ALTITUDE_RATE_MPS * dt:
        return target
    return current + math.copysign(ALTITUDE_RATE_MPS * dt, diff)


def apply_command(
    state: DroneRuntimeState, command_type: str, payload: dict[str, Any]
) -> tuple[bool, str | None]:
    """명령을 기체 상태에 반영한다. `(수락 여부, 실패 사유)`를 돌려준다.

    "수락"은 "지금 당장 실패로 끝낼 이유가 없다"는 뜻이다 — RTL/MOVE_TO가 수락됐다고
    목적지에 바로 도착한 건 아니다. 도착 판정은 `advance_pose`가 매 틱 한다.
    """
    if command_type == "RTL":
        state.mode = "RETURNING"
        state.target_lat, state.target_lon, state.target_alt = BASE_LAT, BASE_LON, RTL_ALTITUDE_M
        return True, None

    if command_type == "MOVE_TO":
        lat, lon = payload.get("target_latitude"), payload.get("target_longitude")
        if lat is None or lon is None:
            return False, "payload에 target_latitude/target_longitude가 없음"
        state.mode = "MOVING_TO"
        state.target_lat, state.target_lon = float(lat), float(lon)
        alt = payload.get("target_altitude_m")
        state.target_alt = float(alt) if alt is not None else state.alt
        return True, None

    if command_type == "LOITER":
        state.mode = "LOITERING"
        state.target_lat, state.target_lon, state.target_alt = state.lat, state.lon, state.alt
        return True, None

    if command_type == "ARM":
        state.armed = True
        return True, None

    if command_type == "DISARM":
        state.armed = False
        return True, None

    if command_type == "SET_ALTITUDE":
        if state.mode == "SCENARIO":
            return False, "기체가 아직 임무경로(SCENARIO) 중 — RTL/MOVE_TO/LOITER로 먼저 전환 필요"
        alt = payload.get("target_altitude_m")
        if alt is None:
            return False, "payload에 target_altitude_m이 없음"
        state.target_alt = float(alt)
        return True, None

    if command_type == "SET_SPEED":
        speed = payload.get("target_speed_mps")
        if speed is None:
            return False, "payload에 target_speed_mps가 없음"
        state.transit_speed_mps = float(speed)
        return True, None

    return False, f"알 수 없는 command_type: {command_type}"


def advance_pose(state: DroneRuntimeState, t: float, dt: float) -> Pose:
    """한 틱(`dt`초) 전진시키고 그 시점의 `Pose`를 반환한다. `state.lat/lon/alt`도
    그 결과로 갱신한다(다음 틱의 출발점이 되므로)."""
    if not state.armed:
        # DISARM: 다음 ARM 전까지 제자리에 얼어붙는다.
        return Pose(
            latitude=state.lat,
            longitude=state.lon,
            altitude_m=state.alt,
            heading_deg=0.0,
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=0.0,
            speed_mps=0.0,
        )

    if state.mode == "SCENARIO":
        pose = state.config.scenario.pose_at(t)
        state.lat, state.lon, state.alt = pose.latitude, pose.longitude, pose.altitude_m
        return pose

    if state.mode == "LOITERING":
        state.alt = _step_altitude(state.alt, state.target_alt, dt)
        return Pose(
            latitude=state.lat,
            longitude=state.lon,
            altitude_m=state.alt,
            heading_deg=0.0,
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=0.0,
            speed_mps=0.0,
        )

    # RETURNING(RTL) / MOVING_TO: 목표 지점까지 직선으로 비행한다. `bearing_deg`/
    # `offset_latlon`은 scenarios/base.py의 기존 지구-평면 근사 수학을 그대로 재사용한다
    # (waypoint 시나리오가 두 지점 사이를 보간하는 것과 같은 원리).
    assert state.target_lat is not None and state.target_lon is not None
    distance_m = horizontal_distance_m(state.lat, state.lon, state.target_lat, state.target_lon)
    step_m = state.transit_speed_mps * dt
    if distance_m <= max(step_m, ARRIVAL_THRESHOLD_M):
        state.lat, state.lon = state.target_lat, state.target_lon
        heading = 0.0
        arrived = True
    else:
        heading = bearing_deg(state.lat, state.lon, state.target_lat, state.target_lon)
        north_m = step_m * math.cos(math.radians(heading))
        east_m = step_m * math.sin(math.radians(heading))
        state.lat, state.lon = offset_latlon(state.lat, state.lon, north_m, east_m)
        arrived = False

    state.alt = _step_altitude(state.alt, state.target_alt, dt)
    altitude_settled = state.target_alt is None or abs(state.alt - state.target_alt) < (
        ALTITUDE_ARRIVAL_THRESHOLD_M
    )
    if arrived and altitude_settled:
        state.mode = "LOITERING"  # 도착 후 그 자리에서 대기 — SET_ALTITUDE/SET_SPEED를
        # 이어서 받을 수 있는 상태가 된다("REQUIRES_ACTIVE_MODE" 참고).

    return Pose(
        latitude=state.lat,
        longitude=state.lon,
        altitude_m=state.alt,
        heading_deg=heading,
        roll_deg=0.0,
        pitch_deg=0.0,
        yaw_deg=to_signed_deg(heading),
        speed_mps=0.0 if arrived else state.transit_speed_mps,
    )


def flight_mode_for(state: DroneRuntimeState) -> FlightMode:
    if not state.armed:
        return FlightMode.MANUAL
    return _MODE_TO_FLIGHT_MODE[state.mode]


class DeviceCommandClient:
    """실시간 루프에서 쓰는 명령 HTTP 클라이언트 — 폴링·ACK·실행·결과 보고.

    네트워크 오류는(`HttpSink`와 같은 원칙, `simulator/simulator/sinks.py`) 예외를
    던지지 않고 표준 에러에 기록만 한다 — 명령 처리 실패가 텔레메트리 전송 자체를
    멈추면 안 된다.
    """

    def __init__(self, api_base_url: str, timeout_s: float = 5.0) -> None:
        self._client = httpx.Client(base_url=api_base_url, timeout=timeout_s)

    def list_dispatched(self) -> list[dict[str, Any]]:
        try:
            response = self._client.get("/commands", params={"status": "DISPATCHED"})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            sys.stderr.write(f"[device] 명령 목록 조회 실패: {exc}\n")
            return []

    def get_detail(self, command_id: str) -> dict[str, Any] | None:
        try:
            response = self._client.get(f"/commands/{command_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            sys.stderr.write(f"[device] 명령 상세 조회 실패({command_id}): {exc}\n")
            return None

    def ack(self, command_id: str) -> bool:
        return self._post(f"/commands/{command_id}/ack")

    def execute(self, command_id: str) -> bool:
        return self._post(f"/commands/{command_id}/execute")

    def result(self, command_id: str, outcome: str, detail: str | None) -> bool:
        body: dict[str, Any] = {"outcome": outcome}
        if detail:
            body["detail"] = {"message": detail}
        return self._post(f"/commands/{command_id}/result", json=body)

    def _post(self, path: str, *, json: dict[str, Any] | None = None) -> bool:
        try:
            response = self._client.post(path, json=json)
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            sys.stderr.write(f"[device] {path} 실패: {exc}\n")
            return False

    def close(self) -> None:
        self._client.close()


def extract_payload(detail_response: dict[str, Any]) -> dict[str, Any]:
    """`GET /commands/{id}` 응답에서 원래 요청 payload를 복원한다.

    `commands` 테이블 자체엔 payload 원문이 없고 해시만 있다(`backend/app/modules/
    command/repository.py`의 `hash_payload` — 감사 로그 외 용도로 원문을 영구 보관할
    이유가 없다는 설계). 대신 생성 시점의 `CREATED` 이벤트가 전체 envelope을
    `detail`에 그대로 남겨둔다(`create_command_idempotent`) — 그래서 거기서 꺼낸다.
    """
    for event in detail_response.get("events", []):
        if event.get("event_type") == "CREATED":
            return (event.get("detail") or {}).get("payload") or {}
    return {}


def poll_and_apply_commands(
    client: DeviceCommandClient, states_by_asset: dict[str, DroneRuntimeState]
) -> None:
    """매 틱 한 번 호출 — 대기 중인 명령을 찾아 아직 바쁘지 않은 기체에 적용하고
    ACK/EXECUTING까지 보고한다. 결과(SUCCEEDED/FAILED) 보고는 `advance_pose` 이후
    `report_completed_commands`가 맡는다(도착 여부를 그 시점에야 알 수 있어서)."""
    dispatched = client.list_dispatched()
    for summary in dispatched:
        command_id = summary["command_id"]
        detail = client.get_detail(command_id)
        if detail is None:
            continue
        asset_id = detail["target_asset_id"]
        state = states_by_asset.get(asset_id)
        if state is None or state.active_command_id is not None:
            continue  # 내가 모르는 기체거나, 이미 다른 명령을 처리 중.

        command_type = detail["command_type"]
        payload = extract_payload(detail)

        if command_type in REQUIRES_ACTIVE_MODE and state.mode == "SCENARIO":
            accepted, reason = False, "기체가 아직 임무경로(SCENARIO) 중"
        else:
            accepted, reason = apply_command(state, command_type, payload)

        if not client.ack(command_id):
            continue
        client.execute(command_id)
        state.active_command_id = command_id
        state.last_processed_command_id = command_id

        if not accepted:
            client.result(command_id, "FAILED", reason)
            state.active_command_id = None
        elif command_type in INSTANT_COMMAND_TYPES:
            client.result(command_id, "SUCCEEDED", None)
            state.active_command_id = None
        # 그 외(RTL/MOVE_TO/SET_ALTITUDE)는 도착해야 끝난다 — active_command_id를
        # 들고 있다가 report_completed_commands가 매 틱 완료 여부를 확인한다.


def report_completed_commands(
    client: DeviceCommandClient, states_by_asset: dict[str, DroneRuntimeState]
) -> None:
    """RTL/MOVE_TO가 목적지에 도착해 `LOITERING`으로 바뀌었으면(`advance_pose` 참고)
    그 시점에 SUCCEEDED를 보고하고 기체를 다시 "안 바쁨" 상태로 되돌린다."""
    for state in states_by_asset.values():
        if state.active_command_id is None:
            continue
        if state.mode == "LOITERING":
            client.result(state.active_command_id, "SUCCEEDED", None)
            state.active_command_id = None


def build_frame(
    drone: DroneConfig,
    pose: Pose,
    *,
    seq: int,
    event_time: datetime,
    battery_pct: float,
    rssi_dbm: float,
    flight_mode: FlightMode,
    mission_id: str | None = None,
) -> TelemetryFrame:
    """`generator.generate_frames`와 같은 필드 조립 로직을 실시간 루프에서도 그대로
    쓴다 — 배터리 소모·RSSI 지터 계산은 호출부(`main.py`)가 맡고, 이 함수는 조립만
    한다(사전계산 경로와 실시간 경로가 서로 다른 프레임 모양을 만들면 두 모드 결과를
    비교할 수 없게 된다)."""
    return TelemetryFrame(
        asset_id=drone.asset_id,
        mission_id=mission_id,
        event_time=event_time,
        sequence_no=seq,
        latitude=pose.latitude,
        longitude=pose.longitude,
        altitude_m=pose.altitude_m,
        speed_mps=pose.speed_mps,
        heading_deg=pose.heading_deg,
        roll_deg=pose.roll_deg,
        pitch_deg=pose.pitch_deg,
        yaw_deg=pose.yaw_deg,
        battery_pct=round(battery_pct, 2),
        rssi_dbm=round(rssi_dbm, 1),
        flight_mode=flight_mode,
    )
