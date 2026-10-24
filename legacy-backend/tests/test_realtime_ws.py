"""4단계 완료 기준 검증: `/ws/operations` 스냅샷과 실시간 갱신(통합 테스트, 실제
Postgres/Redis 필요).

`docs/roadmap/04_단계_2D실시간관제_Day08-10.md`:
- 10대 아이콘이 식별 가능하게 갱신된다 (→ 갱신 이벤트가 실제로 전달되는지 확인).
- 재연결 후 최신 스냅샷으로 복구한다 (→ 매 연결마다 스냅샷을 새로 보내는지 확인).
"""
import time
import uuid

from fastapi.testclient import TestClient


def _frame(asset_id: str, seq: int, event_time: str) -> dict:
    return {
        "asset_id": asset_id,
        "event_time": event_time,
        "sequence_no": seq,
        "latitude": 37.5,
        "longitude": 127.0,
        "altitude_m": 100.0,
        "battery_pct": 90.0,
    }


def test_snapshot_includes_asset_with_prior_telemetry(live_client: TestClient):
    asset_id = f"ws-{uuid.uuid4().hex[:8]}"
    response = live_client.post("/telemetry", json=_frame(asset_id, 0, "2026-01-01T00:00:00Z"))
    assert response.status_code == 202
    time.sleep(0.3)  # consumer가 반영할 시간

    with live_client.websocket_connect("/ws/operations") as ws:
        snapshot = ws.receive_json()
        assert snapshot["type"] == "snapshot"
        assert any(a["asset_id"] == asset_id for a in snapshot["assets"])


def test_live_update_is_pushed_after_connect(live_client: TestClient):
    asset_id = f"ws-{uuid.uuid4().hex[:8]}"

    with live_client.websocket_connect("/ws/operations") as ws:
        ws.receive_json()  # 초기 스냅샷은 건너뛴다

        response = live_client.post(
            "/telemetry", json=_frame(asset_id, 0, "2026-01-01T00:00:00Z")
        )
        assert response.status_code == 202

        update = ws.receive_json()
        assert update["type"] == "update"
        assert update["asset"]["asset_id"] == asset_id
        assert update["asset"]["sequence_no"] == 0


def test_reconnect_gets_fresh_snapshot_without_resume_protocol(live_client: TestClient):
    asset_id = f"ws-{uuid.uuid4().hex[:8]}"
    live_client.post("/telemetry", json=_frame(asset_id, 0, "2026-01-01T00:00:00Z"))
    time.sleep(0.3)

    with live_client.websocket_connect("/ws/operations") as first:
        first.receive_json()

    live_client.post("/telemetry", json=_frame(asset_id, 1, "2026-01-01T00:00:01Z"))
    time.sleep(0.3)

    with live_client.websocket_connect("/ws/operations") as second:
        snapshot = second.receive_json()
        asset = next(a for a in snapshot["assets"] if a["asset_id"] == asset_id)
        assert asset["sequence_no"] == 1  # 재연결한 세션이 최신 상태를 그대로 받는다
