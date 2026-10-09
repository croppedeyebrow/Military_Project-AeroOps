"""3단계 보정 완료 기준 검증: "같은 idempotency key의 명령이 하나만 생성된다"(통합 테스트).

실제 Postgres/Redis가 필요하다(없으면 스킵) — `POST /commands`가 DB에 커밋하고 Command
Redis Stream에도 발행하기 때문이다.

승인·취소·ACK 등 전체 수명주기 테스트는 `test_command_lifecycle.py` 참고.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient


def _envelope(**overrides) -> dict:
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


def test_creates_command_with_201(live_client: TestClient):
    response = live_client.post("/commands", json=_envelope())
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING_APPROVAL"  # 요청 자체가 이미 승인 대기 상태
    assert body["is_new"] is True


def test_same_idempotency_key_returns_existing_command_once(live_client: TestClient):
    envelope = _envelope()

    first = live_client.post("/commands", json=envelope)
    second = live_client.post("/commands", json=envelope)

    assert first.status_code == 201
    assert second.status_code == 200  # 재실행이 아니라 기존 명령을 그대로 반환
    assert first.json()["command_id"] == second.json()["command_id"]
    assert second.json()["is_new"] is False


def test_reused_idempotency_key_with_different_payload_conflicts(live_client: TestClient):
    idempotency_key = f"idem-{uuid.uuid4().hex[:8]}"

    first = live_client.post(
        "/commands", json=_envelope(idempotency_key=idempotency_key, command_type="RTL")
    )
    conflict = live_client.post(
        "/commands",
        json=_envelope(idempotency_key=idempotency_key, command_type="LOITER"),
    )

    assert first.status_code == 201
    assert conflict.status_code == 409


def test_invalid_command_envelope_rejected_with_422(live_client: TestClient):
    invalid = _envelope(expires_at="2020-01-01T00:00:00Z")  # 발급 시각보다 이전
    response = live_client.post("/commands", json=invalid)
    assert response.status_code == 422
