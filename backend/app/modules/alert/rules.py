"""경보 규칙 — 배터리 부족·RSSI 저하·지오펜스 이탈.

`docs/planning/05_데이터엔지니어링_아키텍처.md`: "초기 경보는 설명 가능한 규칙 기반으로
구현하고 ML은 후속 비교 실험으로 둔다." 모든 규칙은 순수 함수라 텔레메트리 파이프라인
없이도 단위 테스트한다. `RULE_VERSION`을 올리면(임계값 변경 등) 이후 생성되는 경보부터
새 버전이 찍혀 "이 경보가 어떤 규칙으로 판정됐는지" 항상 추적할 수 있다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.mission.models import Geofence
from app.schemas.telemetry import TelemetryFrame

RULE_VERSION = "v1"

BATTERY_WARNING_PCT = 20.0
BATTERY_CRITICAL_PCT = 10.0
RSSI_WARNING_DBM = -100.0


@dataclass(frozen=True)
class AlertCandidate:
    alert_type: str
    severity: str
    evidence: dict[str, Any]


def evaluate_battery(frame: TelemetryFrame) -> AlertCandidate | None:
    if frame.battery_pct <= BATTERY_CRITICAL_PCT:
        evidence = {"battery_pct": frame.battery_pct, "threshold": BATTERY_CRITICAL_PCT}
        return AlertCandidate("BATTERY_LOW", "CRITICAL", evidence)
    if frame.battery_pct <= BATTERY_WARNING_PCT:
        evidence = {"battery_pct": frame.battery_pct, "threshold": BATTERY_WARNING_PCT}
        return AlertCandidate("BATTERY_LOW", "WARNING", evidence)
    return None


def evaluate_rssi(frame: TelemetryFrame) -> AlertCandidate | None:
    if frame.rssi_dbm is None:
        return None
    if frame.rssi_dbm <= RSSI_WARNING_DBM:
        return AlertCandidate(
            "RSSI_LOW", "WARNING", {"rssi_dbm": frame.rssi_dbm, "threshold": RSSI_WARNING_DBM}
        )
    return None


def _point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """단순 ray-casting 알고리즘(짝수/홀수 규칙). 링은 `[[lon, lat], ...]`(닫힌 링)."""
    inside = False
    n = len(ring)
    for i in range(n - 1):  # 마지막 점은 첫 점과 같으므로(닫힌 링) 제외
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % (n - 1)]
        x_at_lat = (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-15) + x1
        intersects = (y1 > lat) != (y2 > lat) and lon < x_at_lat
        if intersects:
            inside = not inside
    return inside


def evaluate_geofence(frame: TelemetryFrame, geofences: list[Geofence]) -> AlertCandidate | None:
    """금지 구역(PROHIBITED) 안에 있으면 이탈 경보를 낸다."""
    for geofence in geofences:
        if geofence.zone_type != "PROHIBITED":
            continue
        if _point_in_ring(frame.longitude, frame.latitude, geofence.polygon):
            return AlertCandidate(
                "GEOFENCE_BREACH",
                "CRITICAL",
                {"geofence_id": geofence.id, "geofence_name": geofence.name},
            )
    return None


def evaluate_all(frame: TelemetryFrame, geofences: list[Geofence]) -> list[AlertCandidate]:
    candidates = [
        evaluate_battery(frame),
        evaluate_rssi(frame),
        evaluate_geofence(frame, geofences),
    ]
    return [c for c in candidates if c is not None]
