"""3단계 통합 테스트 공용 fixture.

`DATABASE_URL`/`REDIS_URL`이 가리키는 서비스가 실제로 떠 있을 때만 통합 테스트를
실행한다(CI는 `.github/workflows/ci.yml`에서 postgres/redis 서비스 컨테이너를 띄운다).
로컬에 두 서비스가 없으면 스킵되어 순수 단위 테스트(`test_health.py`,
`test_telemetry_schema.py`)는 계속 빠르게 통과한다.
"""
from collections.abc import Iterator

import pytest
import redis as redis_sync
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import get_settings
from app.main import app


def _services_reachable() -> bool:
    settings = get_settings()
    try:
        engine = create_engine(settings.database_url, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
    except Exception:
        return False

    try:
        client = redis_sync.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
    except Exception:
        return False
    return True


@pytest.fixture(scope="session")
def require_live_services() -> None:
    if not _services_reachable():
        pytest.skip(
            "DATABASE_URL/REDIS_URL에 연결할 수 없어 통합 테스트를 건너뜁니다. "
            "docker compose -f infra/docker-compose.yml up -d postgres redis 로 띄운 뒤 "
            "alembic upgrade head를 실행하세요."
        )


@pytest.fixture(scope="session")
def live_client(require_live_services: None) -> Iterator[TestClient]:
    """lifespan(consumer task 포함)이 활성화된 TestClient.

    세션 스코프로 하나만 만든다 — Redis 클라이언트(`app.core.redis.get_redis`)가
    프로세스 전역 캐시(`lru_cache`)라 asyncio 이벤트 루프에 묶여 있는데, 테스트마다
    새 `TestClient`(= 새 이벤트 루프)를 만들면 이전 루프에 바인딩된 커넥션이 재사용되며
    깨진다. 실제 서버가 이벤트 루프 하나로 계속 떠 있는 상황과도 더 가깝다.
    """
    with TestClient(app) as client:
        yield client
