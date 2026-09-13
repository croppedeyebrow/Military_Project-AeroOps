"""4단계 완료 기준 검증: 재동기화 handshake(통합 테스트, 실제 Postgres/Redis 필요).

`docs/roadmap/04_단계_2D실시간관제_Day08-10.md`:
- 단절 중 누락 구간이 sequence gap으로 남는다.
- 재연결 전후 최신 상태와 command 상태가 모순되지 않는다.
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


def _send_frames(client: TestClient, asset_id: str, count: int) -> None:
    for seq in range(count):
        event_time = f"2026-01-01T00:00:{seq:02d}Z"
        response = client.post("/telemetry", json=_frame(asset_id, seq, event_time))
        assert response.status_code == 202
    _wait_until_stored(client, asset_id, count - 1)


def _wait_until_stored(
    client: TestClient, asset_id: str, expected_last_seq: int, timeout: float = 5.0
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/assets/{asset_id}/latest")
        if response.status_code == 200 and response.json()["sequence_no"] == expected_last_seq:
            return
        time.sleep(0.05)
    raise AssertionError("제한 시간 내에 텔레메트리가 반영되지 않았다")


def test_sync_reports_gap_when_device_claims_ahead_of_server(live_client: TestClient):
    asset_id = f"sync-{uuid.uuid4().hex[:8]}"
    _send_frames(live_client, asset_id, count=5)  # 서버는 sequence_no 0~4를 가진다

    response = live_client.post(f"/devices/{asset_id}/sync", json={"last_sequence_no": 9})
    assert response.status_code == 200
    body = response.json()
    assert body["server_last_sequence_no"] == 4
    assert body["sequence_gap_count"] == 5
    assert body["missing_sequence_numbers"] == [5, 6, 7, 8, 9]
    assert body["snapshot_reissued"] is True
    assert body["latest_state"]["sequence_no"] == 4


def test_sync_flags_anomaly_when_device_behind_server(live_client: TestClient):
    asset_id = f"sync-{uuid.uuid4().hex[:8]}"
    _send_frames(live_client, asset_id, count=5)

    response = live_client.post(f"/devices/{asset_id}/sync", json={"last_sequence_no": 1})
    body = response.json()
    assert body["anomaly"] == "device_behind_server"
    assert body["sequence_gap_count"] == 0
    assert body["snapshot_reissued"] is True


def test_sync_reports_no_gap_when_sequence_matches(live_client: TestClient):
    asset_id = f"sync-{uuid.uuid4().hex[:8]}"
    _send_frames(live_client, asset_id, count=3)

    response = live_client.post(f"/devices/{asset_id}/sync", json={"last_sequence_no": 2})
    body = response.json()
    assert body["sequence_gap_count"] == 0
    assert body["anomaly"] is None
    assert body["snapshot_reissued"] is False
    assert body["latest_state"] is None  # 재발급 불필요하니 스냅샷도 안 보낸다


def test_sync_reports_pending_commands_for_asset(live_client: TestClient):
    asset_id = f"sync-{uuid.uuid4().hex[:8]}"
    _send_frames(live_client, asset_id, count=1)

    command = {
        "command_id": f"cmd-{uuid.uuid4().hex[:8]}",
        "idempotency_key": f"idem-{uuid.uuid4().hex[:8]}",
        "target_asset_id": asset_id,
        "command_type": "RTL",
        "requested_by": "operator-1",
        "issued_at": "2026-01-01T00:00:00Z",
        "expires_at": "2026-01-01T00:05:00Z",
    }
    create_response = live_client.post("/commands", json=command)
    assert create_response.status_code == 201

    response = live_client.post(f"/devices/{asset_id}/sync", json={"last_sequence_no": 0})
    body = response.json()
    assert command["command_id"] in body["pending_command_ids"]


def test_sync_handles_asset_with_no_telemetry_yet(live_client: TestClient):
    asset_id = f"sync-new-{uuid.uuid4().hex[:8]}"
    response = live_client.post(f"/devices/{asset_id}/sync", json={"last_sequence_no": 0})
    assert response.status_code == 200
    body = response.json()
    assert body["server_last_sequence_no"] is None
    assert body["snapshot_reissued"] is False
