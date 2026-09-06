"""경유지 비행 시나리오: 위경도 경유지 목록을 순서대로 순회한다(마지막 이후 처음으로 순환)."""
from __future__ import annotations

from dataclasses import dataclass, field

from simulator.scenarios.base import Pose, bearing_deg, horizontal_distance_m, to_signed_deg


@dataclass(frozen=True)
class Waypoint:
    latitude: float
    longitude: float
    altitude_m: float


@dataclass(frozen=True)
class WaypointScenario:
    waypoints: list[Waypoint]
    speed_mps: float
    _leg_lengths_m: list[float] = field(init=False, repr=False)
    _total_length_m: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if len(self.waypoints) < 2:
            raise ValueError("경유지는 최소 2개 이상이어야 한다(순환 경로 구성)")
        legs = []
        points = [*self.waypoints, self.waypoints[0]]  # 마지막 → 처음으로 순환
        for a, b in zip(points, points[1:]):
            legs.append(horizontal_distance_m(a.latitude, a.longitude, b.latitude, b.longitude))
        object.__setattr__(self, "_leg_lengths_m", legs)
        object.__setattr__(self, "_total_length_m", sum(legs))

    def pose_at(self, t: float) -> Pose:
        distance_along_path = (self.speed_mps * t) % self._total_length_m
        points = [*self.waypoints, self.waypoints[0]]

        remaining = distance_along_path
        for i, leg_length in enumerate(self._leg_lengths_m):
            if remaining <= leg_length or leg_length == 0:
                a, b = points[i], points[i + 1]
                fraction = 0.0 if leg_length == 0 else remaining / leg_length
                lat = a.latitude + (b.latitude - a.latitude) * fraction
                lon = a.longitude + (b.longitude - a.longitude) * fraction
                alt = a.altitude_m + (b.altitude_m - a.altitude_m) * fraction
                heading = bearing_deg(a.latitude, a.longitude, b.latitude, b.longitude)
                return Pose(
                    latitude=lat,
                    longitude=lon,
                    altitude_m=alt,
                    heading_deg=heading,
                    roll_deg=0.0,
                    pitch_deg=0.0,
                    yaw_deg=to_signed_deg(heading),
                    speed_mps=self.speed_mps,
                )
            remaining -= leg_length

        # 부동소수점 오차로 도달: 마지막 경유지에 정지한 것으로 처리한다.
        last = points[0]
        return Pose(
            latitude=last.latitude,
            longitude=last.longitude,
            altitude_m=last.altitude_m,
            heading_deg=0.0,
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=0.0,
            speed_mps=0.0,
        )
