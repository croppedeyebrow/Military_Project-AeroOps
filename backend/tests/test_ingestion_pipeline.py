"""3단계 완료 기준 검증(통합 테스트, 실제 Postgres/Redis 필요).

`docs/roadmap/03_단계_수집저장파이프라인_Day05-07.md`:
- 10대 데이터를 손실 없이 저장한다.
- 중복 데이터가 이중 반영되지 않는다.
- 역순 데이터가 최신 상태를 후퇴시키지 않는다.
- 기간·기체 조건 이력 조회 테스트가 통과한다.

`POST /telemetry`는 Redis Stream에 발행만 하고 실제 DB 반영은 백그라운드 consumer가
비동기로 처리하므로(`docs/planning/02_백엔드_아키텍처.md`), 테스트에서는 결과가 보일
때까지 짧게 폴링한다(고정 sleep보다 빠르고 안정적).
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


def _history(client: TestClient, asset_id: str, **params) -> dict:
    response = client.get(f"/assets/{asset_id}/telemetry", params=params)
    assert response.status_code == 200
    return response.json()


def _wait_for_history_count(client: TestClient, asset_id: str, min_count: int) -> dict:
    """history의 count가 `min_count` 이상이 될 때까지 폴링한 뒤 그 결과를 반환한다."""

    def _check() -> dict | None:
        history = _history(client, asset_id)
        return history if history["count"] >= min_count else None

    return _wait_until(_check)


def _wait_for_latest_sequence(client: TestClient, asset_id: str, sequence_no: int) -> None:
    def _check() -> bool | None:
        response = client.get(f"/assets/{asset_id}/latest")
        return True if response.json().get("sequence_no") == sequence_no else None

    _wait_until(_check)


def test_frames_stored_without_loss(live_client: TestClient):
    asset_id = f"test-{uuid.uuid4().hex[:8]}"
    for seq in range(10):
        response = live_client.post(
            "/telemetry", json=_frame(asset_id, seq, f"2026-01-01T00:00:{seq:02d}Z")
        )
        assert response.status_code == 202

    history = _wait_for_history_count(live_client, asset_id, 10)
    assert history["count"] == 10
    assert [item["sequence_no"] for item in history["items"]] == list(range(10))


def test_duplicate_frame_not_double_counted(live_client: TestClient):
    asset_id = f"test-{uuid.uuid4().hex[:8]}"
    frame = _frame(asset_id, 0, "2026-01-01T00:00:00Z")

    assert live_client.post("/telemetry", json=frame).status_code == 202
    assert live_client.post("/telemetry", json=frame).status_code == 202  # 동일 프레임 재전송

    _wait_for_history_count(live_client, asset_id, 1)
    time.sleep(0.3)  # 두 번째(중복) 메시지가 처리될 여유를 준다
    history = _history(live_client, asset_id)
    assert history["count"] == 1


def test_out_of_order_frame_does_not_regress_latest_state(live_client: TestClient):
    asset_id = f"test-{uuid.uuid4().hex[:8]}"

    live_client.post("/telemetry", json=_frame(asset_id, 0, "2026-01-01T00:00:00Z"))
    live_client.post("/telemetry", json=_frame(asset_id, 1, "2026-01-01T00:00:05Z"))
    _wait_for_latest_sequence(live_client, asset_id, 1)

    # 역순(과거 event_time) 프레임을 나중에 수신한다.
    stale_response = live_client.post(
        "/telemetry", json=_frame(asset_id, 99, "2025-01-01T00:00:00Z")
    )
    assert stale_response.status_code == 202

    history = _wait_for_history_count(live_client, asset_id, 3)
    assert history["count"] == 3  # 원본은 보존된다

    latest = live_client.get(f"/assets/{asset_id}/latest").json()
    assert latest["sequence_no"] == 1  # 최신 상태는 후퇴하지 않는다


def test_history_query_filters_by_time_range(live_client: TestClient):
    asset_id = f"test-{uuid.uuid4().hex[:8]}"
    for seq in range(5):
        live_client.post("/telemetry", json=_frame(asset_id, seq, f"2026-01-01T00:00:{seq:02d}Z"))
    _wait_for_history_count(live_client, asset_id, 5)

    filtered = _history(
        live_client, asset_id, start="2026-01-01T00:00:02Z", end="2026-01-01T00:00:03Z"
    )
    assert [item["sequence_no"] for item in filtered["items"]] == [2, 3]


def test_history_query_paginates(live_client: TestClient):
    asset_id = f"test-{uuid.uuid4().hex[:8]}"
    for seq in range(5):
        live_client.post("/telemetry", json=_frame(asset_id, seq, f"2026-01-01T00:00:{seq:02d}Z"))
    _wait_for_history_count(live_client, asset_id, 5)

    page = _history(live_client, asset_id, limit=2, offset=1)
    assert [item["sequence_no"] for item in page["items"]] == [1, 2]


def test_invalid_frame_rejected_with_422(live_client: TestClient):
    asset_id = f"test-{uuid.uuid4().hex[:8]}"
    invalid = _frame(asset_id, 0, "2026-01-01T00:00:00Z", latitude=999.0)
    response = live_client.post("/telemetry", json=invalid)
    assert response.status_code == 422


def test_latest_state_404_for_unknown_asset(live_client: TestClient):
    response = live_client.get(f"/assets/unknown-{uuid.uuid4().hex[:8]}/latest")
    assert response.status_code == 404


def test_list_assets_includes_asset_with_latest_state(live_client: TestClient):
    asset_id = f"test-{uuid.uuid4().hex[:8]}"
    live_client.post("/telemetry", json=_frame(asset_id, 0, "2026-01-01T00:00:00Z"))

    def _find_asset() -> dict | None:
        listed = live_client.get("/assets").json()
        return next((a for a in listed if a["asset_id"] == asset_id), None)

    match = _wait_until(_find_asset)
    assert match["sequence_no"] == 0
