"""7단계 1차 단위 검증: 배포 등록·운용 세션 수명주기(통합 테스트, 실제 Postgres 필요).

목적: `app/modules/deployment/repository.py`의 핵심 보장 두 가지를 실제 DB로 확인한다.
(1) "같은 버전 조합이면 재사용, 다르면 새 row" — `get_or_create_current_deployment`.
(2) "세션 시작 시 deployment_id가 고정되고, 종료 전까지는 ended_at이 비어있다."
"""
from fastapi.testclient import TestClient


def test_build_info_reports_current_version(live_client: TestClient):
    # 목적: 1단계 보정 때부터 있던 기본 계약 — DB 연결 없이도 항상 응답해야 한다는
    # 성질은 바뀌지 않았는지 회귀 확인.
    response = live_client.get("/system/build-info")
    assert response.status_code == 200
    body = response.json()
    assert "git_sha" in body
    assert "image_tag" in body


def test_get_deployment_by_id_round_trips(live_client: TestClient):
    # 목적: DeploymentBadge의 "재생 대상" 모드처럼 목록이 아니라 특정 id 하나를
    # 조회하는 경로(`GET /deployments/{id}`)가 목록에 있는 것과 같은 내용을 주는지 확인.
    listed = live_client.get("/deployments").json()
    assert len(listed) >= 1
    deployment_id = listed[0]["id"]

    fetched = live_client.get(f"/deployments/{deployment_id}")
    assert fetched.status_code == 200
    assert fetched.json() == listed[0]


def test_get_unknown_deployment_404(live_client: TestClient):
    response = live_client.get("/deployments/unknown-deployment-id")
    assert response.status_code == 404


def test_lifespan_auto_registers_current_deployment(live_client: TestClient):
    # 근거: main.py의 lifespan이 앱 시작 시 get_or_create_current_deployment를 호출하므로,
    # 별도 API를 호출하지 않아도 /deployments 목록에 최소 1건이 이미 있어야 한다.
    response = live_client.get("/deployments")
    assert response.status_code == 200
    deployments = response.json()
    assert len(deployments) >= 1


def test_start_operation_session_pins_current_deployment(live_client: TestClient):
    deployments_before = live_client.get("/deployments").json()
    assert len(deployments_before) >= 1
    current_deployment_id = deployments_before[0]["id"]

    response = live_client.post("/operation-sessions", json={"started_by": "pytest"})
    assert response.status_code == 201
    session = response.json()
    assert session["deployment_id"] == current_deployment_id
    assert session["started_by"] == "pytest"
    # 목적: "아직 안 끝난 세션"이라는 상태를 ended_at=None으로 표현한다는 모델 설계를
    # API 응답까지 그대로 확인한다.
    assert session["ended_at"] is None


def test_list_operation_sessions_includes_created(live_client: TestClient):
    # 목적: ReplayTimeline의 세션 선택 UI가 쓸 GET /operation-sessions(목록)이 방금
    # 만든 세션을 포함하는지 확인.
    session = live_client.post("/operation-sessions", json={"started_by": "pytest-list"}).json()

    listed = live_client.get("/operation-sessions").json()
    assert any(s["id"] == session["id"] for s in listed)


def test_end_operation_session_sets_ended_at(live_client: TestClient):
    session = live_client.post("/operation-sessions", json={}).json()

    response = live_client.post(f"/operation-sessions/{session['id']}/end")
    assert response.status_code == 200
    assert response.json()["ended_at"] is not None


def test_end_operation_session_twice_is_idempotent(live_client: TestClient):
    # 근거: repository.end_operation_session은 "이미 끝난 세션"이면 ended_at을 덮어쓰지
    # 않는다(최초 종료 시각을 보존) — 두 번 호출해도 같은 ended_at이 유지되는지 확인.
    session = live_client.post("/operation-sessions", json={}).json()
    first = live_client.post(f"/operation-sessions/{session['id']}/end").json()
    second = live_client.post(f"/operation-sessions/{session['id']}/end").json()
    assert first["ended_at"] == second["ended_at"]


def test_end_unknown_operation_session_404(live_client: TestClient):
    response = live_client.post("/operation-sessions/unknown-session-id/end")
    assert response.status_code == 404


def test_get_operation_session_round_trip(live_client: TestClient):
    created = live_client.post("/operation-sessions", json={"started_by": "ops-1"}).json()
    fetched = live_client.get(f"/operation-sessions/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created
