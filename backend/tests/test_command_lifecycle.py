"""5단계 완료 기준 검증: 명령 상태 전이(승인/취소/ACK/실행/결과/타임아웃), 감사 로그.

`docs/roadmap/05_단계_임무경보관리_Day11-13.md`:
- 승인되지 않았거나 만료된 명령은 전달되지 않는다.
- ACK 손실 시 명령을 무조건 재실행하지 않는다.
- 취소 가능·불가능 상태가 정책과 일치한다.
"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.modules.command.timeout_worker import sweep_timed_out_commands


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


def _create(live_client: TestClient, **overrides) -> dict:
    envelope = _envelope(**overrides)
    response = live_client.post("/commands", json=envelope)
    assert response.status_code == 201
    return envelope


def test_approve_auto_dispatches_when_not_expired(live_client: TestClient):
    envelope = _create(live_client)
    response = live_client.post(
        f"/commands/{envelope['command_id']}/approve", json={"approved_by": "supervisor-1"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "DISPATCHED"


def test_self_approval_rejected(live_client: TestClient):
    envelope = _create(live_client, requested_by="operator-1")
    response = live_client.post(
        f"/commands/{envelope['command_id']}/approve", json={"approved_by": "operator-1"}
    )
    assert response.status_code == 403


def test_approve_already_expired_command_times_out_instead_of_dispatching(
    live_client: TestClient,
):
    now = datetime.now(timezone.utc)
    envelope = _create(
        live_client,
        issued_at=(now - timedelta(minutes=10)).isoformat(),
        expires_at=(now - timedelta(minutes=1)).isoformat(),
    )
    response = live_client.post(
        f"/commands/{envelope['command_id']}/approve", json={"approved_by": "supervisor-1"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "TIMED_OUT"


def test_approve_unknown_command_404(live_client: TestClient):
    response = live_client.post(
        "/commands/does-not-exist/approve", json={"approved_by": "supervisor-1"}
    )
    assert response.status_code == 404


def test_double_approve_rejected_as_invalid_transition(live_client: TestClient):
    envelope = _create(live_client)
    first = live_client.post(
        f"/commands/{envelope['command_id']}/approve", json={"approved_by": "supervisor-1"}
    )
    assert first.json()["status"] == "DISPATCHED"

    second = live_client.post(
        f"/commands/{envelope['command_id']}/approve", json={"approved_by": "supervisor-2"}
    )
    assert second.status_code == 409


def test_cancel_from_pending_approval_succeeds(live_client: TestClient):
    envelope = _create(live_client)
    response = live_client.post(
        f"/commands/{envelope['command_id']}/cancel",
        json={"cancelled_by": "operator-1", "reason": "임무 취소"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_cancel_after_executing_is_rejected(live_client: TestClient):
    envelope = _create(live_client)
    command_id = envelope["command_id"]
    live_client.post(f"/commands/{command_id}/approve", json={"approved_by": "supervisor-1"})
    live_client.post(f"/commands/{command_id}/ack")
    live_client.post(f"/commands/{command_id}/execute")

    response = live_client.post(
        f"/commands/{command_id}/cancel", json={"cancelled_by": "operator-1"}
    )
    assert response.status_code == 409


def test_full_lifecycle_to_succeeded(live_client: TestClient):
    envelope = _create(live_client)
    command_id = envelope["command_id"]

    assert live_client.post(
        f"/commands/{command_id}/approve", json={"approved_by": "supervisor-1"}
    ).json()["status"] == "DISPATCHED"
    assert live_client.post(f"/commands/{command_id}/ack").json()["status"] == "ACKNOWLEDGED"
    assert live_client.post(f"/commands/{command_id}/execute").json()["status"] == "EXECUTING"

    result = live_client.post(f"/commands/{command_id}/result", json={"outcome": "SUCCEEDED"})
    assert result.status_code == 200
    assert result.json()["status"] == "SUCCEEDED"

    detail = live_client.get(f"/commands/{command_id}").json()
    event_types = [e["event_type"] for e in detail["events"]]
    assert event_types == [
        "CREATED",
        "APPROVED",
        "DISPATCHED",
        "ACKNOWLEDGED",
        "EXECUTING",
        "SUCCEEDED",
    ]


def test_ack_without_dispatch_is_rejected_not_auto_retried(live_client: TestClient):
    """ACK가 DISPATCHED 상태를 전제하므로, 아직 전달 전인 명령에 대한 ACK는 거부된다 —
    시스템 어디에도 "자동 재실행" 경로가 없으므로 이 거부가 곧 "ACK 손실 시 무조건
    재실행 안 함"을 만족시킨다.
    """
    envelope = _create(live_client)  # PENDING_APPROVAL 상태, 아직 승인 전
    response = live_client.post(f"/commands/{envelope['command_id']}/ack")
    assert response.status_code == 409


def test_list_commands_filters_by_status(live_client: TestClient):
    envelope = _create(live_client)
    response = live_client.get("/commands", params={"status": "PENDING_APPROVAL"})
    assert response.status_code == 200
    ids = [c["command_id"] for c in response.json()]
    assert envelope["command_id"] in ids


def test_approve_records_audit_event(live_client: TestClient):
    envelope = _create(live_client)
    command_id = envelope["command_id"]
    live_client.post(f"/commands/{command_id}/approve", json={"approved_by": "supervisor-1"})

    logs = live_client.get(
        "/audit-logs", params={"target_type": "command", "target_id": command_id}
    ).json()
    actions = [entry["action"] for entry in logs]
    assert "command.create" in actions
    assert "command.approve" in actions


def test_timeout_worker_sweeps_expired_pending_commands(live_client: TestClient):
    now = datetime.now(timezone.utc)
    envelope = _create(
        live_client,
        issued_at=(now - timedelta(minutes=10)).isoformat(),
        expires_at=(now - timedelta(seconds=1)).isoformat(),
    )

    # `live_client`의 lifespan이 이미 백그라운드 timeout worker를 띄워두고 있어(5초 주기)
    # 그쪽이 먼저 스윕했을 수도 있다 — 그래서 반환 건수(count)가 아니라 최종 상태만 확인한다.
    sweep_timed_out_commands()

    detail = live_client.get(f"/commands/{envelope['command_id']}").json()
    assert detail["status"] == "TIMED_OUT"
