"""AeroOps FastAPI 진입점.

1단계(프로젝트 기반) 완료 기준: `/health/live`, `/health/ready`가 응답하고
프론트엔드가 이를 조회할 수 있어야 한다. 실제 도메인 라우터는 이후 단계에서
`app/modules/*`에 구현되어 이 파일에 등록된다.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AeroOps API",
    description="가상 드론 관제 플랫폼 API",
    version="0.1.0",
)

# TODO(2단계 이후): 배포 환경에 맞춰 origin을 제한한다. (04_인프라_네트워크_클라우드.md)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health/live", tags=["health"])
def health_live() -> dict:
    """프로세스가 살아있는지 확인한다."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
def health_ready() -> dict:
    """DB/Redis 등 의존 리소스 준비 상태 확인.

    TODO(3단계): 실제 DB/Redis 커넥션 확인 로직 추가.
    """
    return {"status": "ok", "env": settings.app_env}


# TODO: 아래 라우터들은 로드맵 단계에 맞춰 순차적으로 등록한다.
# from app.modules.ingestion.router import router as ingestion_router
# from app.modules.telemetry.router import router as telemetry_router
# from app.modules.mission.router import router as mission_router
# from app.modules.alert.router import router as alert_router
# from app.modules.realtime.router import router as realtime_router
# from app.modules.identity.router import router as identity_router
# from app.modules.audit.router import router as audit_router
# app.include_router(ingestion_router)
# app.include_router(telemetry_router)
# app.include_router(mission_router)
# app.include_router(alert_router)
# app.include_router(realtime_router)
# app.include_router(identity_router)
# app.include_router(audit_router)
