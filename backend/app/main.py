"""AeroOps FastAPI 진입점.

3단계(`docs/roadmap/03_단계_수집저장파이프라인_Day05-07.md`)에서 수집(`ingestion`)·조회
(`telemetry`) 라우터를 등록하고, Redis Streams consumer를 백그라운드 task로 띄운다
(`docs/planning/02_백엔드_아키텍처.md`: "오래 걸리는 분석을 요청 경로에서 실행하지 않는다").
"""
import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from app.core.config import get_settings
from app.core.metrics import telemetry_rejected_total
from app.core.redis import get_redis
from app.core.redis_acl import ensure_channel_acl_users
from app.db.base import SessionLocal
from app.modules.command.router import router as command_router
from app.modules.deployment.router import router as deployment_router
from app.modules.ingestion.router import router as ingestion_router
from app.modules.realtime.router import router as realtime_router
from app.modules.sync.router import router as sync_router
from app.modules.telemetry.consumer import run_consumer_loop
from app.modules.telemetry.router import router as telemetry_router

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """앱 수명 동안 Telemetry/Command 채널 ACL을 등록하고 consumer를 하나 띄운다.

    ADR 0001(단일 프로세스 모놀리스)에 따라 별도 워커 프로세스를 두지 않는다.
    """
    try:
        await ensure_channel_acl_users()
    except Exception:
        # 관리형 Redis 등 ACL 명령이 막힌 환경도 있을 수 있다 — 채널 분리가 강제되지
        # 않을 뿐 서비스 자체는 계속 띄운다(`app/core/redis_acl.py` docstring 참고).
        logger.warning("Redis ACL 채널 사용자 등록 실패 — 채널 분리 없이 계속 진행", exc_info=True)

    consumer_task = asyncio.create_task(run_consumer_loop())
    try:
        yield
    finally:
        consumer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await consumer_task


app = FastAPI(
    title="AeroOps API",
    description="가상 드론 관제 플랫폼 API",
    version="0.1.0",
    lifespan=lifespan,
)

# TODO(8단계): 배포 환경에 맞춰 origin을 제한한다. (04_인프라_네트워크_클라우드.md)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """계약 위반 요청을 표준 422로 응답하되, 수집 경로는 거부량 메트릭에 반영한다."""
    if request.url.path == "/telemetry":
        telemetry_rejected_total.inc()
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})


@app.get("/health/live", tags=["health"])
def health_live() -> dict:
    """프로세스가 살아있는지 확인한다."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def health_ready() -> JSONResponse:
    """DB/Redis 연결 상태를 확인한다."""
    checks = {"database": False, "redis": False}

    def _check_db() -> bool:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True

    try:
        checks["database"] = await asyncio.to_thread(_check_db)
    except Exception:
        logger.exception("DB health check 실패")

    try:
        checks["redis"] = bool(await get_redis().ping())
    except Exception:
        logger.exception("Redis health check 실패")

    healthy = all(checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "env": settings.app_env,
            "checks": checks,
        },
    )


app.include_router(ingestion_router)
app.include_router(telemetry_router)
app.include_router(deployment_router)
app.include_router(command_router)
app.include_router(realtime_router)
app.include_router(sync_router)

# TODO: 아래 라우터들은 로드맵 단계에 맞춰 순차적으로 등록한다.
# from app.modules.mission.router import router as mission_router
# from app.modules.alert.router import router as alert_router
# from app.modules.identity.router import router as identity_router
# from app.modules.audit.router import router as audit_router
# from app.modules.device_identity.router import router as device_identity_router
# app.include_router(mission_router)
# app.include_router(alert_router)
# app.include_router(identity_router)
# app.include_router(audit_router)
# app.include_router(device_identity_router)
