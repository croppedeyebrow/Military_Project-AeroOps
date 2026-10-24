"""7단계 2차 단위 검증: 4개 채널(telemetry/command/alert/sync)이 모두 `event_log`에
정규화 이벤트를 남기는지(통합 테스트, 실제 Postgres/Redis 필요).

목적: `append_event_log`를 각 모듈(telemetry consumer, command/alert/sync repository)에
연결한 것이 실제로 동작하는지 — `GET /event-log`로 확인한다(단위가 작아서 아직 재생
엔진은 없다 — 조회만 검증. 재생 엔진은 다음 작은 단위).
"""
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient


def _wait_until(predicate, timeout: float = 5.0, interval: float = 0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result is not None:
            return result
        time.sleep(interval)
    pytest.fail("제한 시간 내에 조건을 만족하지 못했다(consumer 처리 지연 또는 실패)")


def _frame(asset_id: str, seq: int, event_time: str, **overrides) -> dict:
    base = {
        "asset_id": asset_id,
        "event_time": event_time,
        "sequence_no": seq,
        "latitude": 37.5,
        "longitude": 127.0,
        "altitude_m": 100.0,
        "battery_pct": 90.0,
    }
    base.update(overrides)
    return base


def _event_log_for_asset(client: TestClient, asset_id: str) -> list[dict]:
    # source_channel=telemetry로 좁혀서, 이 테스트가 만든 프레임이 아닌 다른 테스트의
    # command/alert 이벤트와 섞이지 않게 한다.
    response = client.get("/event-log", params={"source_channel": "telemetry"})
    assert response.status_code == 200
    return [e for e in response.json() if e["payload"] and e["payload"].get("asset_id") == asset_id]


def test_telemetry_frame_appends_event_log_entry(live_client: TestClient):
    asset_id = f"test-evt-{uuid.uuid4().hex[:8]}"
    live_client.post("/telemetry", json=_frame(asset_id, 0, "2026-01-01T00:00:00Z"))

    entries = _wait_until(lambda: _event_log_for_asset(live_client, asset_id) or None)
    assert len(entries) == 1
    assert entries[0]["event_type"] == "telemetry.received"
    assert entries[0]["stream_sequence"] == 0
    assert entries[0]["payload"]["is_new"] is True


def test_duplicate_and_reordered_frames_are_both_logged(live_client: TestClient):
    # 목적: "최신 상태를 바꾼 것만"이 아니라 "수신된 모든 프레임"이 event_log에 남아야
    # 한다는 설계 결정(consumer.py 주석 참고)을 검증한다 — 중복·역순도 빠지면 안 된다.
    asset_id = f"test-evt-{uuid.uuid4().hex[:8]}"
    frame0 = _frame(asset_id, 0, "2026-01-01T00:00:00Z")
    frame1 = _frame(asset_id, 1, "2026-01-01T00:00:05Z")

    live_client.post("/telemetry", json=frame0)
    live_client.post("/telemetry", json=frame1)
    live_client.post("/telemetry", json=frame0)  # 중복 재전송

    entries = _wait_until(
        lambda: (e if len(e := _event_log_for_asset(live_client, asset_id)) == 3 else None)
    )
    assert sorted(e["stream_sequence"] for e in entries) == [0, 0, 1]
    duplicate_entry = next(
        e for e in entries if e["stream_sequence"] == 0 and not e["payload"]["is_new"]
    )
    assert duplicate_entry["payload"]["latest_updated"] is False


def test_event_log_ordered_by_event_time_not_arrival(live_client: TestClient):
    # 목적: list_event_log가 event_time 기준으로 정렬한다는 설계(repository.py docstring)를
    # 확인한다 — 역순으로 도착했어도 조회 결과는 event_time 순서여야 한다.
    asset_id = f"test-evt-{uuid.uuid4().hex[:8]}"
    later = _frame(asset_id, 5, "2026-01-01T00:10:00Z")
    earlier = _frame(asset_id, 4, "2026-01-01T00:05:00Z")

    live_client.post("/telemetry", json=later)  # 늦은(사건상 나중) 프레임이 먼저 도착
    live_client.post("/telemetry", json=earlier)  # 이른 프레임이 나중에 도착(역순)

    entries = _wait_until(
        lambda: (e if len(e := _event_log_for_asset(live_client, asset_id)) == 2 else None)
    )
    # 재정렬하지 않고 API가 돌려준 순서 그대로 검증한다 — 정렬 자체가 서버 책임
    # (`list_event_log`)이라는 걸 테스트가 대신 해버리면 그 책임이 깨져도 못 잡아낸다.
    assert [e["stream_sequence"] for e in entries] == [4, 5]


def _command_envelope(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    base = {
        "command_id": f"cmd-{uuid.uuid4().hex[:8]}",
        "idempotency_key": f"idem-{uuid.uuid4().hex[:8]}",
        "target_asset_id": "drone-01",
        "command_type": "RTL",
        "requested_by": "operator-1",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=5)).isoformat(),
    }
    base.update(overrides)
    return base


def _event_log_by_correlation(
    client: TestClient, source_channel: str, correlation_id: str
) -> list[dict]:
    response = client.get("/event-log", params={"source_channel": source_channel})
    assert response.status_code == 200
    return [e for e in response.json() if e["correlation_id"] == correlation_id]


def test_command_lifecycle_appends_event_log_entries(live_client: TestClient):
    # 목적: command/repository.py의 단일 `_transition` 헬퍼에 건 `append_event_log`가
    # 생성(CREATED)과 승인에 따른 자동 전달(APPROVED→DISPATCHED)까지 전부 잡는지 확인.
    envelope = _command_envelope()
    command = live_client.post("/commands", json=envelope).json()
    live_client.post(
        f"/commands/{command['command_id']}/approve", json={"approved_by": "approver-1"}
    )

    entries = _event_log_by_correlation(live_client, "command", command["command_id"])
    event_types = [e["event_type"] for e in entries]
    assert event_types == ["command.CREATED", "command.APPROVED", "command.DISPATCHED"]


def test_battery_alert_appends_event_log_entry(live_client: TestClient):
    # 목적: alert/repository.py의 evaluate_and_raise_alerts가 새 경보를 만들 때
    # event_log에도 "alert.OPENED"를 남기는지 확인.
    asset_id = f"test-evt-{uuid.uuid4().hex[:8]}"
    live_client.post(
        "/telemetry",
        json={
            "asset_id": asset_id,
            "event_time": "2026-01-01T00:00:00Z",
            "sequence_no": 0,
            "latitude": 37.5,
            "longitude": 127.0,
            "altitude_m": 100.0,
            "battery_pct": 5.0,  # BATTERY_CRITICAL_PCT(10%) 이하
        },
    )

    def _check():
        response = live_client.get("/event-log", params={"source_channel": "alert"})
        matches = [e for e in response.json() if e["payload"].get("asset_id") == asset_id]
        return matches or None

    entries = _wait_until(_check)
    assert entries[0]["event_type"] == "alert.OPENED"
    assert entries[0]["payload"]["alert_type"] == "BATTERY_LOW"


def test_device_sync_appends_event_log_entry(live_client: TestClient):
    # 목적: sync/repository.py의 perform_sync가 매 호출마다 event_log에 "sync.PERFORMED"를
    # 남기는지 확인(재동기화는 완료 기준의 핵심 장면이라 재생에서 보여야 한다).
    asset_id = f"test-evt-{uuid.uuid4().hex[:8]}"
    response = live_client.post(f"/devices/{asset_id}/sync", json={"last_sequence_no": 0})
    assert response.status_code == 200

    entries_response = live_client.get("/event-log", params={"source_channel": "sync"})
    matches = [e for e in entries_response.json() if e["payload"].get("asset_id") == asset_id]
    assert len(matches) == 1
    assert matches[0]["event_type"] == "sync.PERFORMED"
