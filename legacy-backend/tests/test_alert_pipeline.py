"""5단계 완료 기준 검증: 3종 경보가 실제 텔레메트리 파이프라인을 통해 재현되는지
(통합 테스트, 실제 Postgres/Redis 필요).

`docs/roadmap/05_단계_임무경보관리_Day11-13.md`: "세 종류의 경보가 시나리오에 맞게
재현된다", "경보마다 판단 근거와 규칙 버전을 조회한다".
"""

import time
import uuid

from fastapi.testclient import TestClient


def _frame(asset_id: str, seq: int, **overrides) -> dict:
    base = {
        "asset_id": asset_id,
        "event_time": f"2026-01-01T00:00:{seq:02d}Z",
        "sequence_no": seq,
        "latitude": 37.5,
        "longitude": 127.0,
        "altitude_m": 100.0,
        "battery_pct": 90.0,
    }
    base.update(overrides)
    return base


def _wait_until(predicate, timeout: float = 5.0, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result is not None:
            return result
        time.sleep(interval)
    raise AssertionError("제한 시간 내에 조건을 만족하지 못했다")


def test_battery_low_alert_is_raised_and_queryable(live_client: TestClient):
    asset_id = f"alert-{uuid.uuid4().hex[:8]}"
    live_client.post("/telemetry", json=_frame(asset_id, 0, battery_pct=5.0))

    def _find_open_alert():
        alerts = live_client.get("/alerts", params={"asset_id": asset_id, "status": "OPEN"}).json()
        return alerts[0] if alerts else None

    alert = _wait_until(_find_open_alert)
    assert alert["alert_type"] == "BATTERY_LOW"
    assert alert["severity"] == "CRITICAL"
    assert alert["rule_version"]
    assert alert["evidence"]["battery_pct"] == 5.0


def test_rssi_low_alert_is_raised(live_client: TestClient):
    asset_id = f"alert-{uuid.uuid4().hex[:8]}"
    live_client.post("/telemetry", json=_frame(asset_id, 0, rssi_dbm=-115.0))

    def _find_open_alert():
        alerts = live_client.get("/alerts", params={"asset_id": asset_id, "status": "OPEN"}).json()
        return alerts[0] if alerts else None

    alert = _wait_until(_find_open_alert)
    assert alert["alert_type"] == "RSSI_LOW"


def test_geofence_breach_alert_is_raised(live_client: TestClient):
    asset_id = f"alert-{uuid.uuid4().hex[:8]}"
    geofence_id = f"gf-{uuid.uuid4().hex[:8]}"
    polygon = [[126.99, 37.49], [127.01, 37.49], [127.01, 37.51], [126.99, 37.51], [126.99, 37.49]]
    live_client.post(
        "/geofences",
        json={
            "id": geofence_id,
            "name": "테스트 금지구역",
            "zone_type": "PROHIBITED",
            "polygon": polygon,
        },
    )

    live_client.post("/telemetry", json=_frame(asset_id, 0, latitude=37.5, longitude=127.0))

    def _find_open_alert():
        alerts = live_client.get("/alerts", params={"asset_id": asset_id, "status": "OPEN"}).json()
        return alerts[0] if alerts else None

    alert = _wait_until(_find_open_alert)
    assert alert["alert_type"] == "GEOFENCE_BREACH"
    assert alert["evidence"]["geofence_id"] == geofence_id


def test_repeated_low_battery_frames_do_not_duplicate_open_alert(live_client: TestClient):
    asset_id = f"alert-{uuid.uuid4().hex[:8]}"
    for seq in range(5):
        live_client.post("/telemetry", json=_frame(asset_id, seq, battery_pct=5.0))

    def _count_open_alerts():
        alerts = live_client.get("/alerts", params={"asset_id": asset_id, "status": "OPEN"}).json()
        return len(alerts) if alerts else None

    _wait_until(_count_open_alerts)
    time.sleep(0.3)  # 나머지 프레임들이 처리될 여유
    alerts = live_client.get("/alerts", params={"asset_id": asset_id, "status": "OPEN"}).json()
    battery_alerts = [a for a in alerts if a["alert_type"] == "BATTERY_LOW"]
    assert len(battery_alerts) == 1


def test_acknowledge_then_resolve_alert(live_client: TestClient):
    asset_id = f"alert-{uuid.uuid4().hex[:8]}"
    live_client.post("/telemetry", json=_frame(asset_id, 0, battery_pct=5.0))

    def _find_open_alert():
        alerts = live_client.get("/alerts", params={"asset_id": asset_id, "status": "OPEN"}).json()
        return alerts[0] if alerts else None

    alert = _wait_until(_find_open_alert)
    alert_id = alert["id"]

    ack = live_client.post(
        f"/alerts/{alert_id}/acknowledge", json={"acknowledged_by": "operator-1"}
    )
    assert ack.status_code == 200
    assert ack.json()["status"] == "ACKNOWLEDGED"

    resolve = live_client.post(f"/alerts/{alert_id}/resolve", json={"resolved_by": "operator-1"})
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "RESOLVED"

    # 이미 해제된 경보를 다시 해제하려 하면 거부된다.
    again = live_client.post(f"/alerts/{alert_id}/resolve", json={"resolved_by": "operator-1"})
    assert again.status_code == 409
