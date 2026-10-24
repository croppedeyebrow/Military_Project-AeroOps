"""5단계 완료 기준 검증: 임무·예정경로·구역 CRUD(통합 테스트, 실제 Postgres 필요)."""

import uuid

from fastapi.testclient import TestClient


def test_create_and_get_mission(live_client: TestClient):
    response = live_client.post("/missions", json={"name": "정찰 임무 A"})
    assert response.status_code == 201
    mission = response.json()
    assert mission["status"] == "PLANNED"

    fetched = live_client.get(f"/missions/{mission['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "정찰 임무 A"


def test_get_unknown_mission_404(live_client: TestClient):
    response = live_client.get(f"/missions/unknown-{uuid.uuid4().hex[:8]}")
    assert response.status_code == 404


def test_list_missions_includes_created(live_client: TestClient):
    created = live_client.post("/missions", json={"name": "목록 확인용 임무"}).json()
    listed = live_client.get("/missions").json()
    assert any(m["id"] == created["id"] for m in listed)


def test_update_mission_status_partial(live_client: TestClient):
    mission = live_client.post("/missions", json={"name": "상태 변경 임무"}).json()

    response = live_client.patch(f"/missions/{mission['id']}", json={"status": "ACTIVE"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ACTIVE"
    assert body["name"] == "상태 변경 임무"  # 안 보낸 필드는 그대로


def test_set_and_get_mission_route(live_client: TestClient):
    mission = live_client.post("/missions", json={"name": "경로 임무"}).json()
    waypoints = [[127.0, 37.5, 100.0], [127.01, 37.51, 100.0], [127.02, 37.5, 100.0]]

    set_response = live_client.put(
        f"/missions/{mission['id']}/route", json={"waypoints": waypoints}
    )
    assert set_response.status_code == 201
    assert set_response.json()["waypoints"] == waypoints

    get_response = live_client.get(f"/missions/{mission['id']}/route")
    assert get_response.status_code == 200
    assert get_response.json()["waypoints"] == waypoints


def test_route_requires_at_least_two_points(live_client: TestClient):
    mission = live_client.post("/missions", json={"name": "경로 부족 임무"}).json()
    response = live_client.put(
        f"/missions/{mission['id']}/route", json={"waypoints": [[127.0, 37.5, 100.0]]}
    )
    assert response.status_code == 422


def test_route_replan_keeps_history_returns_latest(live_client: TestClient):
    mission = live_client.post("/missions", json={"name": "재계획 임무"}).json()
    first_route = [[127.0, 37.5, 100.0], [127.01, 37.51, 100.0]]
    second_route = [[128.0, 38.5, 100.0], [128.01, 38.51, 100.0]]

    live_client.put(f"/missions/{mission['id']}/route", json={"waypoints": first_route})
    live_client.put(f"/missions/{mission['id']}/route", json={"waypoints": second_route})

    latest = live_client.get(f"/missions/{mission['id']}/route").json()
    assert latest["waypoints"] == second_route


def test_create_and_list_geofence(live_client: TestClient):
    geofence_id = f"gf-{uuid.uuid4().hex[:8]}"
    polygon = [[126.99, 37.49], [127.01, 37.49], [127.01, 37.51], [126.99, 37.51], [126.99, 37.49]]

    response = live_client.post(
        "/geofences",
        json={
            "id": geofence_id,
            "name": "금지구역 A",
            "zone_type": "PROHIBITED",
            "polygon": polygon,
        },
    )
    assert response.status_code == 201

    listed = live_client.get("/geofences").json()
    assert any(g["id"] == geofence_id for g in listed)


def test_geofence_rejects_unknown_zone_type(live_client: TestClient):
    polygon = [[126.99, 37.49], [127.01, 37.49], [127.01, 37.51], [126.99, 37.51], [126.99, 37.49]]
    response = live_client.post(
        "/geofences",
        json={"id": "gf-bad", "name": "이상한 구역", "zone_type": "NOT_A_TYPE", "polygon": polygon},
    )
    assert response.status_code == 422


def test_geofence_rejects_unclosed_ring(live_client: TestClient):
    polygon = [[126.99, 37.49], [127.01, 37.49], [127.01, 37.51]]  # 첫 점 != 마지막 점
    response = live_client.post(
        "/geofences",
        json={
            "id": "gf-unclosed",
            "name": "안 닫힌 구역",
            "zone_type": "MISSION",
            "polygon": polygon,
        },
    )
    assert response.status_code == 422
