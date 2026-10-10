"""7단계 재생 엔진 1차 단위 검증(통합 테스트, 실제 Postgres/Redis 필요).

목적: `GET /operation-sessions/{id}/replay`가 (1) 세션 메타데이터와 이벤트를 함께
돌려주고, (2) `order=event_time`/`order=arrival` 두 정렬 모드가 실제로 다르게 동작
하는지 확인한다.
"""
import time
import uuid

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


def test_replay_session_includes_metadata_and_events(live_client: TestClient):
    # 목적: 세션을 새로 만들면 이벤트가 아직 없으니 events=[]이어야 하고, session
    # 메타데이터(id/deployment_id 등)는 그대로 돌아와야 한다. 지금 이 프로세스가
    # lifespan에서 자동 시작한 "현재 세션"과는 다른 세션이라, 다른 모듈이 백그라운드로
    # 기록하는 이벤트가 섞여 들어올 일이 없다 — 그래서 빈 리스트를 안전하게 기대할 수 있다.
    session = live_client.post("/operation-sessions", json={"started_by": "pytest"}).json()

    response = live_client.get(f"/operation-sessions/{session['id']}/replay")
    assert response.status_code == 200
    body = response.json()
    assert body["session"]["id"] == session["id"]
    assert body["order"] == "event_time"
    assert body["events"] == []


def test_replay_session_not_found_404(live_client: TestClient):
    response = live_client.get("/operation-sessions/unknown-session/replay")
    assert response.status_code == 404


def test_event_log_order_event_time_vs_arrival_differ_on_reorder(live_client: TestClient):
    # 목적: 역순으로 도착한 두 프레임을 두 정렬 모드로 각각 조회했을 때, event_time
    # 모드는 "사건 발생 순서"(과거→미래)로, arrival 모드는 "도착 순서"(실제 들어온
    # 순서, 즉 미래가 먼저 들어왔으니 미래 먼저)로 서로 다르게 나오는지 확인한다.
    asset_id = f"test-replay-{uuid.uuid4().hex[:8]}"
    later = {
        "asset_id": asset_id,
        "event_time": "2026-01-01T00:10:00Z",
        "sequence_no": 5,
        "latitude": 37.5,
        "longitude": 127.0,
        "altitude_m": 100.0,
        "battery_pct": 90.0,
    }
    earlier = {**later, "event_time": "2026-01-01T00:05:00Z", "sequence_no": 4}

    live_client.post("/telemetry", json=later)  # 나중 사건이 먼저 도착
    live_client.post("/telemetry", json=earlier)  # 이전 사건이 나중에 도착(역순)

    def _matching(order: str) -> list[dict] | None:
        params = {"source_channel": "telemetry", "order": order}
        response = live_client.get("/event-log", params=params)
        matches = [e for e in response.json() if e["payload"].get("asset_id") == asset_id]
        return matches if len(matches) == 2 else None

    event_time_order = _wait_until(lambda: _matching("event_time"))
    arrival_order = _matching("arrival")

    assert [e["stream_sequence"] for e in event_time_order] == [4, 5]  # 발생 순서
    assert [e["stream_sequence"] for e in arrival_order] == [5, 4]  # 도착 순서(역순 그대로)
