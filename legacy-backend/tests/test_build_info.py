"""1단계 보정 완료 기준 검증: 실행 중인 코드·이미지·스키마 버전 조회.

`docs/roadmap/작업분해_2단계_8단계.md` "1단계 보정": 장애 시 어떤 버전이 돌고 있었는지
역추적할 수 있어야 한다.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_build_info_reports_git_sha_and_image_tag():
    response = client.get("/system/build-info")
    assert response.status_code == 200
    body = response.json()
    assert body["git_sha"]  # 기본값("local-dev")이라도 비어있지는 않다
    assert body["image_tag"]


def test_build_info_reports_schema_version_from_migrations():
    response = client.get("/system/build-info")
    body = response.json()
    # DB 연결 없이도(코드가 포함한 migration 스크립트 기준) head revision을 알 수 있어야 한다.
    # 정확한 revision 문자열은 migration이 추가될 때마다 바뀌므로 값 자체가 아니라
    # "비어있지 않은 문자열"만 확인한다.
    assert isinstance(body["schema_version"], str)
    assert body["schema_version"]
