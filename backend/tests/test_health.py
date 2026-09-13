"""1단계 완료 기준 검증: health endpoint 응답."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_live():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_ready_reports_dependency_checks():
    """3단계부터 실제 DB/Redis 연결을 확인한다(`docs/planning/04_인프라_네트워크_클라우드.md`).

    로컬에 DB/Redis가 없는 환경에서도 이 테스트 자체는 통과해야 하므로, 응답 형태만
    검증한다. 실제로 두 의존성이 모두 살아있을 때 200/ok가 되는지는
    `tests/test_ingestion_pipeline.py`(통합 테스트, DB·Redis 필요)에서 확인한다.
    """
    response = client.get("/health/ready")
    body = response.json()
    assert response.status_code in (200, 503)
    assert body["status"] in ("ok", "degraded")
    assert set(body["checks"]) == {"database", "redis"}
