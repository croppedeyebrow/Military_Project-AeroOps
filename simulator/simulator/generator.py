"""드론 편대 생성기: seed 기반으로 재현 가능한 정상 TelemetryFrame 시퀀스를 만든다.

`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day0304.md` 완료 기준:
"동일 seed 실행 결과가 일치한다" — 이를 위해 전역 seed에서
`numpy.random.SeedSequence.spawn`으로 기체별 독립 RNG 스트림을 파생한다
(기체 수·순서가 같으면 항상 같은 스트림을 얻는다).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

from simulator.contracts.telemetry import FlightMode, TelemetryFrame
from simulator.scenarios import CircleScenario, Scenario, StraightScenario, Waypoint, WaypointScenario

# 기본 편대 기준점(가상 좌표 — 실제 지명과 무관).
BASE_LAT = 37.5
BASE_LON = 127.0

BATTERY_DRAIN_PCT_PER_HOUR = 6.0
RSSI_BASE_DBM = -60.0
RSSI_JITTER_STD_DBM = 2.0


@dataclass(frozen=True)
class DroneConfig:
    asset_id: str
    scenario: Scenario
    start_battery_pct: float
    rng: np.random.Generator


def build_scenario(name: str, index: int, rng: np.random.Generator) -> Scenario:
    """기체 인덱스·RNG로 살짝 다른 파라미터를 가진 시나리오 인스턴스를 만든다.

    같은 종류의 기체라도 겹치지 않게(반경/시작각/고도를 벌려) 화면에서 구분 가능하도록 한다.
    """
    altitude_m = 100.0 + index * 10.0

    if name == "circle":
        radius_m = 300.0 + index * 40.0
        start_angle = float(rng.uniform(0, 360))
        return CircleScenario(
            center_lat=BASE_LAT,
            center_lon=BASE_LON,
            altitude_m=altitude_m,
            radius_m=radius_m,
            speed_mps=12.0,
            clockwise=index % 2 == 0,
            start_angle_deg=start_angle,
        )
    if name == "straight":
        heading = float(rng.uniform(0, 360))
        return StraightScenario(
            start_lat=BASE_LAT + index * 0.01,
            start_lon=BASE_LON,
            altitude_m=altitude_m,
            leg_length_m=1500.0,
            speed_mps=15.0,
            heading_deg=heading,
        )
    if name == "waypoint":
        offset = index * 0.01
        waypoints = [
            Waypoint(BASE_LAT + offset, BASE_LON, altitude_m),
            Waypoint(BASE_LAT + offset + 0.01, BASE_LON + 0.01, altitude_m),
            Waypoint(BASE_LAT + offset, BASE_LON + 0.02, altitude_m),
            Waypoint(BASE_LAT + offset - 0.01, BASE_LON + 0.01, altitude_m),
        ]
        return WaypointScenario(waypoints=waypoints, speed_mps=13.0)

    raise ValueError(f"알 수 없는 시나리오: {name} (circle|straight|waypoint 중 선택)")


def build_fleet(seed: int, num_drones: int, scenario_name: str) -> list[DroneConfig]:
    """seed로부터 `num_drones`대의 독립적이고 재현 가능한 기체 설정을 만든다."""
    seed_sequence = np.random.SeedSequence(seed)
    child_seeds = seed_sequence.spawn(num_drones)

    fleet: list[DroneConfig] = []
    for i, child_seed in enumerate(child_seeds):
        rng = np.random.default_rng(child_seed)
        scenario = build_scenario(scenario_name, i, rng)
        fleet.append(
            DroneConfig(
                asset_id=f"drone-{i + 1:02d}",
                scenario=scenario,
                start_battery_pct=float(rng.uniform(90, 100)),
                rng=rng,
            )
        )
    return fleet


def generate_frames(
    drone: DroneConfig,
    *,
    start_time: datetime,
    frequency_hz: float,
    duration_s: float,
    mission_id: str | None = None,
) -> list[TelemetryFrame]:
    """한 기체의 정상 프레임 시퀀스를 생성한다(장애 주입 이전 상태)."""
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    interval_s = 1.0 / frequency_hz
    num_ticks = int(duration_s * frequency_hz)

    frames: list[TelemetryFrame] = []
    for seq in range(num_ticks):
        t = seq * interval_s
        pose = drone.scenario.pose_at(t)

        battery_pct = max(0.0, drone.start_battery_pct - BATTERY_DRAIN_PCT_PER_HOUR * (t / 3600.0))
        rssi = float(RSSI_BASE_DBM + drone.rng.normal(0, RSSI_JITTER_STD_DBM))
        rssi = min(0.0, max(-130.0, rssi))

        frames.append(
            TelemetryFrame(
                asset_id=drone.asset_id,
                mission_id=mission_id,
                event_time=start_time + timedelta(seconds=t),
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
                rssi_dbm=round(rssi, 1),
                flight_mode=FlightMode.AUTO,
            )
        )
    return frames


def scenario_run_id(scenario_name: str, seed: int) -> str:
    """재현성 추적용 식별자. 로그·메트릭에서 실행을 구분하는 데 쓴다."""
    return f"{scenario_name}-seed{seed}"
