"""비행 시나리오 공통 인터페이스와 좌표 유틸리티.

모든 시나리오는 시간 `t`(초, 시나리오 시작 기준)를 받아 결정론적으로
`Pose`를 반환한다. 동일 파라미터(및 seed로 정해지는 초기 조건)에 대해 항상
같은 결과를 내야 재현성(`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day0304.md`
완료 기준)이 성립한다.

지구를 국소 평면으로 근사(equirectangular)한다 — MVP 시뮬레이션 정확도로 충분하고,
`docs/planning/03_데이터베이스_아키텍처.md`의 WGS84 표현과도 호환된다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

EARTH_RADIUS_M = 6_371_000.0
METERS_PER_DEG_LAT = 111_320.0


@dataclass(frozen=True)
class Pose:
    latitude: float
    longitude: float
    altitude_m: float
    heading_deg: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    speed_mps: float


class Scenario(Protocol):
    """`pose_at(t)`만 만족하면 시나리오로 취급한다."""

    def pose_at(self, t: float) -> Pose: ...


def normalize_deg(angle_deg: float) -> float:
    """각도를 [0, 360)으로 정규화한다."""
    return angle_deg % 360.0


def to_signed_deg(angle_deg: float) -> float:
    """각도를 [-180, 180]으로 정규화한다. `yaw_deg`/`roll_deg` 범위(계약)에 맞출 때 쓴다."""
    wrapped = normalize_deg(angle_deg)
    return wrapped - 360.0 if wrapped > 180.0 else wrapped


def meters_per_deg_lon(at_latitude_deg: float) -> float:
    return METERS_PER_DEG_LAT * math.cos(math.radians(at_latitude_deg))


def offset_latlon(
    origin_lat: float, origin_lon: float, north_m: float, east_m: float
) -> tuple[float, float]:
    """기준점에서 북쪽/동쪽으로 각각 north_m/east_m 이동한 위경도를 근사 계산한다."""
    lat = origin_lat + north_m / METERS_PER_DEG_LAT
    lon = origin_lon + east_m / meters_per_deg_lon(origin_lat)
    return lat, lon


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 지점 사이의 진방위각(0=N, 90=E)을 계산한다."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)
    x = math.sin(delta_lon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(
        delta_lon
    )
    return normalize_deg(math.degrees(math.atan2(x, y)))


def horizontal_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 지점 사이의 대략적인 지면 거리(m). GPS 점프 장애 검증에 사용한다."""
    north_m = (lat2 - lat1) * METERS_PER_DEG_LAT
    east_m = (lon2 - lon1) * meters_per_deg_lon((lat1 + lat2) / 2)
    return math.hypot(north_m, east_m)
