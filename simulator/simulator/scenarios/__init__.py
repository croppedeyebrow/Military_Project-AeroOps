"""비행 시나리오: 원형, 직선, 경유지.

각 시나리오는 시간에 따른 위치·자세·속도를 결정론적으로 생성한다
(`base.Scenario.pose_at(t)`). 실제 난수가 필요한 요소(초기 위치 분산 등)는
`simulator.generator`에서 seed 기반 RNG로 주입한다.
"""
from simulator.scenarios.base import Pose, Scenario
from simulator.scenarios.circle import CircleScenario
from simulator.scenarios.straight import StraightScenario
from simulator.scenarios.waypoint import Waypoint, WaypointScenario

__all__ = [
    "Pose",
    "Scenario",
    "CircleScenario",
    "StraightScenario",
    "Waypoint",
    "WaypointScenario",
]
