"""직선 비행 시나리오: 두 지점(왕복 경로 양 끝) 사이를 일정 속도로 왕복한다."""
from __future__ import annotations

import math
from dataclasses import dataclass

from simulator.scenarios.base import Pose, offset_latlon, to_signed_deg


@dataclass(frozen=True)
class StraightScenario:
    start_lat: float
    start_lon: float
    altitude_m: float
    leg_length_m: float
    speed_mps: float
    heading_deg: float = 90.0  # 최초 진행 방향(0=N, 90=E)

    def pose_at(self, t: float) -> Pose:
        leg_duration_s = self.leg_length_m / self.speed_mps
        cycle = t % (2 * leg_duration_s)
        outbound = cycle < leg_duration_s
        progress_m = self.speed_mps * (cycle if outbound else cycle - leg_duration_s)

        heading = self.heading_deg if outbound else to_signed_deg(self.heading_deg + 180.0)
        heading_norm = heading % 360.0

        north_m = progress_m * math.cos(math.radians(heading_norm))
        east_m = progress_m * math.sin(math.radians(heading_norm))
        lat, lon = offset_latlon(self.start_lat, self.start_lon, north_m, east_m)

        return Pose(
            latitude=lat,
            longitude=lon,
            altitude_m=self.altitude_m,
            heading_deg=heading_norm,
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=to_signed_deg(heading_norm),
            speed_mps=self.speed_mps,
        )
