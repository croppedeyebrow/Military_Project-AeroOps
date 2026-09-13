"""`GET /system/build-info` — 실행 중인 코드·이미지·스키마 버전 조회.

1단계 보정(`docs/roadmap/작업분해_2단계_8단계.md` "1단계 보정"): 장애 발생 시 "지금 도는
코드가 정확히 무엇인지"를 역추적하기 위한 최소 endpoint.
`docs/planning/04_인프라_네트워크_클라우드.md`: "이미지 digest, Git commit SHA, migration·
schema·rule 버전을 배포 메타데이터로 등록한다."

`deployments`/`operation_sessions` 테이블 기반의 정식 등록·조회 API는 7단계에서 추가한다
(README 참고). 이 endpoint는 그 전까지도 "지금 이 프로세스가 어떤 버전인지"를 바로 확인할 수
있게 한다.
"""
from pathlib import Path

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/system", tags=["deployment"])

# backend/app/modules/deployment/router.py -> parents[3] == backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _current_schema_version() -> str | None:
    """alembic migration 스크립트 기준 head revision(코드가 기대하는 스키마 버전).

    DB에 실제 적용된 버전이 아니라 "이 코드가 요구하는" 버전이다 — DB 연결 없이 계산되므로
    DB가 잠깐 내려가 있어도 build-info 자체는 계속 응답한다(DB 연결 상태는 `/health/ready`가
    별도로 다룬다).
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        alembic_ini = _BACKEND_ROOT / "alembic.ini"
        config = Config(str(alembic_ini))
        config.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
        script_dir = ScriptDirectory.from_config(config)
        return script_dir.get_current_head()
    except Exception:
        return None


@router.get("/build-info")
def get_build_info() -> dict:
    settings = get_settings()
    return {
        "git_sha": settings.git_sha,
        "image_tag": settings.image_tag,
        "schema_version": _current_schema_version(),
    }
