"""AeroOps FastAPI 진입점.

3단계(`docs/roadmap/03_단계_수집저장파이프라인_Day05-07.md`)에서 수집(`ingestion`)·조회
(`telemetry`) 라우터를 등록하고, Redis Streams consumer를 백그라운드 task로 띄운다
(`docs/planning/02_백엔드_아키텍처.md`: "오래 걸리는 분석을 요청 경로에서 실행하지 않는다").
"""
import asyncio
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
from app.core.runtime_state import set_current_operation_session
from app.db.base import SessionLocal
from app.modules.alert.router import router as alert_router
from app.modules.audit.router import router as audit_router
from app.modules.command.router import router as command_router
from app.modules.command.timeout_worker import run_timeout_worker
from app.modules.deployment.repository import (
    end_operation_session,
    get_or_create_current_deployment,
    start_operation_session,
)
from app.modules.deployment.router import router as deployment_router
from app.modules.ingestion.router import router as ingestion_router
from app.modules.mission.router import router as mission_router
from app.modules.realtime.router import router as realtime_router
from app.modules.sync.router import router as sync_router
from app.modules.telemetry.consumer import run_consumer_loop
from app.modules.telemetry.router import router as telemetry_router

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 수명 동안 Telemetry/Command 채널 ACL을 등록하고 consumer를 하나 띄운다.

    ADR 0001(단일 프로세스 모놀리스)에 따라 별도 워커 프로세스를 두지 않는다.

    7단계 추가: 프로세스가 시작될 때 "현재 배포"를 등록하고 운용 세션을 하나 자동으로
    연다. 목적은 `docs/planning/04_인프라_네트워크_클라우드.md` "모든 운용 세션 시작 시
    현재 deployment_id를 고정한다"를 지키는 것 — 아직 사용자 로그인/식별 체계(8단계
    identity 모듈)가 없어 "운영자가 명시적으로 세션을 시작"하는 UI 동작이 없으므로,
    대신 "이 프로세스가 살아있는 동안"을 하나의 운용 세션으로 본다. 이후 단계에서
    실제 로그인이 생기면 이 자동 시작 대신 로그인 시점에 세션을 열도록 바꾼다.
    """
    try:
        await ensure_channel_acl_users()
    except Exception:
        # 관리형 Redis 등 ACL 명령이 막힌 환경도 있을 수 있다 — 채널 분리가 강제되지
        # 않을 뿐 서비스 자체는 계속 띄운다(`app/core/redis_acl.py` docstring 참고).
        logger.warning("Redis ACL 채널 사용자 등록 실패 — 채널 분리 없이 계속 진행", exc_info=True)

    # app.state에 세션 id를 저장해 다른 모듈(이후 event_log 기록 단위)이 "지금 운용
    # 세션"을 참조할 수 있게 한다. DB가 아직 안 떠있는 등의 이유로 실패해도 앱 자체는
    # 계속 띄운다 — build-info처럼 "배포 조회"는 DB 없이도 동작해야 하는 기능이 아니라
    # 그냥 "역추적용 부가 정보"이므로, 이것 때문에 서비스 전체가 죽으면 안 된다.
    app.state.operation_session_id = None
    try:
        with SessionLocal() as db:
            deployment = get_or_create_current_deployment(db)
            session = start_operation_session(db, started_by=None, deployment_id=deployment.id)
            app.state.operation_session_id = session.id
            # `app.state`는 요청 핸들러 전용이라 백그라운드 task(consumer 등)가 못 읽는다
            # (`app/core/runtime_state.py` docstring 참고) — 거기서도 읽을 수 있게 같은
            # 값을 전역 상태 모듈에도 넣어둔다. 두 군데 보관이 중복처럼 보이지만, 용도가
            # 다르다: app.state는 "이 FastAPI 앱 인스턴스에 속한 값"이라는 통상적 관례를
            # 지키는 쪽(테스트에서 app 인스턴스별로 독립적으로 보이길 원할 수 있음),
            # runtime_state는 "asyncio task도 접근 가능한 값"이라는 실질적 필요를 채운다.
            set_current_operation_session(session.id, deployment.id)
            logger.info(
                "운용 세션 시작: session_id=%s deployment_id=%s", session.id, deployment.id
            )
    except Exception:
        logger.warning(
            "운용 세션 자동 시작 실패 — 역추적용 세션 연결 없이 계속 진행", exc_info=True
        )

    consumer_task = asyncio.create_task(run_consumer_loop())
    timeout_worker_task = asyncio.create_task(run_timeout_worker())
    try:
        yield
    finally:
        for task in (consumer_task, timeout_worker_task):
            task.cancel()
        await asyncio.gather(consumer_task, timeout_worker_task, return_exceptions=True)

        # 프로세스가 깨끗하게 종료되는 경우(컨테이너 재시작 등) 세션을 닫아 재생 화면에서
        # "언제까지가 이 배포였는지" 범위가 명확하게 남도록 한다. 비정상 종료(kill -9 등)는
        # 어차피 못 잡으므로 ended_at이 null로 남을 수 있다 — 이는 "비정상 종료됨"이라는
        # 신호로 해석할 수 있어 오히려 유용한 정보다(별도 처리 불필요).
        if app.state.operation_session_id:
            try:
                with SessionLocal() as db:
                    end_operation_session(db, app.state.operation_session_id)
            except Exception:
                logger.warning("운용 세션 종료 기록 실패", exc_info=True)


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
app.include_router(mission_router)
app.include_router(alert_router)
app.include_router(audit_router)

# TODO: 아래 라우터들은 로드맵 단계에 맞춰 순차적으로 등록한다.
# from app.modules.identity.router import router as identity_router
# from app.modules.device_identity.router import router as device_identity_router
# app.include_router(identity_router)
# app.include_router(device_identity_router)
