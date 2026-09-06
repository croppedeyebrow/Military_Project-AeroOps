"""비행 시나리오가 결정론적이고 계약 범위 내 자세값을 내는지 검증한다."""
import math

from simulator.scenarios.base import horizontal_distance_m
from simulator.scenarios.circle import CircleScenario
from simulator.scenarios.straight import StraightScenario
from simulator.scenarios.waypoint import Waypoint, WaypointScenario


def _assert_pose_in_contract_range(pose) -> None:
    assert -90 <= pose.latitude <= 90
    assert -180 <= pose.longitude <= 180
    assert -90 <= pose.pitch_deg <= 90
    assert -180 <= pose.roll_deg <= 180
    assert -180 <= pose.yaw_deg <= 180
    assert 0 <= pose.heading_deg < 360


def test_circle_scenario_stays_near_radius():
    scenario = CircleScenario(
        center_lat=37.5, center_lon=127.0, altitude_m=100.0, radius_m=300.0, speed_mps=12.0
    )
    period_s = 2 * math.pi * scenario.radius_m / scenario.speed_mps
    for fraction in (0.0, 0.25, 0.5, 0.75):
        pose = scenario.pose_at(period_s * fraction)
        _assert_pose_in_contract_range(pose)
        distance = horizontal_distance_m(
            scenario.center_lat, scenario.center_lon, pose.latitude, pose.longitude
        )
        assert abs(distance - scenario.radius_m) < 5.0  # 근사 계산 오차 허용


def test_circle_scenario_deterministic():
    scenario = CircleScenario(
        center_lat=37.5, center_lon=127.0, altitude_m=100.0, radius_m=300.0, speed_mps=12.0
    )
    assert scenario.pose_at(10.0) == scenario.pose_at(10.0)


def test_straight_scenario_reverses_at_leg_end():
    scenario = StraightScenario(
        start_lat=37.5, start_lon=127.0, altitude_m=100.0, leg_length_m=1000.0, speed_mps=10.0
    )
    leg_duration_s = scenario.leg_length_m / scenario.speed_mps

    start_pose = scenario.pose_at(0.0)
    mid_outbound = scenario.pose_at(leg_duration_s / 2)
    mid_return = scenario.pose_at(leg_duration_s * 1.5)

    _assert_pose_in_contract_range(start_pose)
    _assert_pose_in_contract_range(mid_outbound)
    _assert_pose_in_contract_range(mid_return)

    # 복귀 구간(return leg)의 heading은 왕복 방향이므로 출발 heading과 약 180도 차이난다.
    heading_diff = abs(mid_outbound.heading_deg - mid_return.heading_deg) % 360
    assert min(heading_diff, 360 - heading_diff) > 170


def test_waypoint_scenario_completes_loop():
    waypoints = [
        Waypoint(37.50, 127.00, 100.0),
        Waypoint(37.51, 127.01, 100.0),
        Waypoint(37.50, 127.02, 100.0),
        Waypoint(37.49, 127.01, 100.0),
    ]
    scenario = WaypointScenario(waypoints=waypoints, speed_mps=13.0)

    start_pose = scenario.pose_at(0.0)
    _assert_pose_in_contract_range(start_pose)
    assert abs(start_pose.latitude - waypoints[0].latitude) < 1e-6
    assert abs(start_pose.longitude - waypoints[0].longitude) < 1e-6

    # 전체 경로 길이를 한 바퀴 돈 시점엔 다시 첫 경유지 근방이어야 한다.
    looped_pose = scenario.pose_at(scenario._total_length_m / scenario.speed_mps)
    _assert_pose_in_contract_range(looped_pose)
    distance = horizontal_distance_m(
        waypoints[0].latitude, waypoints[0].longitude, looped_pose.latitude, looped_pose.longitude
    )
    assert distance < 5.0
