"""원형 비행 시나리오: 중심점 주위를 일정 반경·속도로 선회한다."""
from __future__ import annotations

import math
from dataclasses import dataclass

from simulator.scenarios.base import Pose, normalize_deg, offset_latlon, to_signed_deg

# 정상 선회(coordinated turn) 시 표현용 고정 뱅크각. 물리 정밀도보다 "회전 중임을
# 시각적으로 구분 가능하게" 하는 목적이 우선이다(2D/3D 관제 검증용, 04~06단계에서 사용).
BANK_ANGLE_DEG = 15.0


@dataclass(frozen=True)
class CircleScenario:
    center_lat: float
    center_lon: float
    altitude_m: float
    radius_m: float
    speed_mps: float
    clockwise: bool = True
    start_angle_deg: float = 0.0

    def pose_at(self, t: float) -> Pose:
        angular_speed = self.speed_mps / self.radius_m  # rad/s
        direction = 1.0 if self.clockwise else -1.0
        angle_rad = math.radians(self.start_angle_deg) + direction * angular_speed * t

        north_m = self.radius_m * math.cos(angle_rad)
        east_m = self.radius_m * math.sin(angle_rad)
        lat, lon = offset_latlon(self.center_lat, self.center_lon, north_m, east_m)

        # 진행 방향(접선 벡터)의 방위각. clockwise일 때 반경 벡터에서 +90도.
        heading = normalize_deg(math.degrees(angle_rad) + direction * 90.0)

        return Pose(
            latitude=lat,
            longitude=lon,
            altitude_m=self.altitude_m,
            heading_deg=heading,
            roll_deg=direction * BANK_ANGLE_DEG,
            pitch_deg=0.0,
            yaw_deg=to_signed_deg(heading),
            speed_mps=self.speed_mps,
        )
