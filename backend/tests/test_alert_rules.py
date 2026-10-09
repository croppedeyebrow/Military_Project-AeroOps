"""순수 로직 단위 테스트: 경보 규칙(서비스 없이도 항상 통과)."""
from datetime import datetime, timezone

from app.modules.alert.rules import (
    BATTERY_CRITICAL_PCT,
    BATTERY_WARNING_PCT,
    RSSI_WARNING_DBM,
    evaluate_all,
    evaluate_battery,
    evaluate_geofence,
    evaluate_rssi,
)
from app.modules.mission.models import Geofence
from app.schemas.telemetry import TelemetryFrame


def _frame(**overrides) -> TelemetryFrame:
    base = {
        "asset_id": "drone-01",
        "event_time": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "sequence_no": 0,
        "latitude": 37.5,
        "longitude": 127.0,
        "altitude_m": 100.0,
        "battery_pct": 90.0,
    }
    base.update(overrides)
    return TelemetryFrame(**base)


def test_battery_ok_produces_no_alert():
    assert evaluate_battery(_frame(battery_pct=BATTERY_WARNING_PCT + 1)) is None


def test_battery_warning_threshold():
    candidate = evaluate_battery(_frame(battery_pct=BATTERY_WARNING_PCT))
    assert candidate is not None
    assert candidate.severity == "WARNING"


def test_battery_critical_threshold():
    candidate = evaluate_battery(_frame(battery_pct=BATTERY_CRITICAL_PCT))
    assert candidate is not None
    assert candidate.severity == "CRITICAL"


def test_rssi_ok_produces_no_alert():
    assert evaluate_rssi(_frame(rssi_dbm=RSSI_WARNING_DBM + 10)) is None


def test_rssi_low_produces_warning():
    candidate = evaluate_rssi(_frame(rssi_dbm=RSSI_WARNING_DBM))
    assert candidate is not None
    assert candidate.alert_type == "RSSI_LOW"


def test_rssi_none_produces_no_alert():
    assert evaluate_rssi(_frame(rssi_dbm=None)) is None


def _geofence(polygon: list[list[float]], zone_type: str = "PROHIBITED") -> Geofence:
    return Geofence(id="gf-1", name="테스트 구역", zone_type=zone_type, polygon=polygon)


# 위경도 (127.0, 37.5) 주변을 두르는 정사각형(약 0.01도 ~ 1km 안쪽)
_SQUARE_AROUND_POINT = [
    [126.99, 37.49],
    [127.01, 37.49],
    [127.01, 37.51],
    [126.99, 37.51],
    [126.99, 37.49],
]


def test_geofence_breach_inside_prohibited_zone():
    geofence = _geofence(_SQUARE_AROUND_POINT)
    candidate = evaluate_geofence(_frame(latitude=37.5, longitude=127.0), [geofence])
    assert candidate is not None
    assert candidate.alert_type == "GEOFENCE_BREACH"


def test_geofence_outside_prohibited_zone_no_alert():
    geofence = _geofence(_SQUARE_AROUND_POINT)
    candidate = evaluate_geofence(_frame(latitude=40.0, longitude=130.0), [geofence])
    assert candidate is None


def test_geofence_non_prohibited_zone_type_never_alerts():
    geofence = _geofence(_SQUARE_AROUND_POINT, zone_type="MISSION")
    candidate = evaluate_geofence(_frame(latitude=37.5, longitude=127.0), [geofence])
    assert candidate is None


def test_evaluate_all_combines_all_rules():
    geofence = _geofence(_SQUARE_AROUND_POINT)
    frame = _frame(latitude=37.5, longitude=127.0, battery_pct=5.0, rssi_dbm=-110.0)
    candidates = evaluate_all(frame, [geofence])
    alert_types = {c.alert_type for c in candidates}
    assert alert_types == {"BATTERY_LOW", "RSSI_LOW", "GEOFENCE_BREACH"}
