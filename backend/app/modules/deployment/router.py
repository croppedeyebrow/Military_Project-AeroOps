"""Deployment/OperationSession API.

- `GET /system/build-info`: 1단계 보정에서 만든 최소 endpoint. "지금 이 프로세스가 어떤
  버전인지"를 DB 연결 없이 바로 확인한다(`app/modules/deployment/repository.py`의
  `current_schema_version()`을 그대로 쓴다 — DB 조회 없이 alembic head만 읽는 그 함수).
- `GET /deployments`: 7단계에서 추가. `deployments` row 목록(최근 등록 순) — 운영자가
  "최근에 뭐가 바뀌었는지" 확인하거나, 재생 화면에서 특정 배포를 선택할 때 쓴다.
- `POST /operation-sessions` / `POST /operation-sessions/{id}/end` / `GET
  /operation-sessions/{id}`: 운용 구간 수명주기. 시작 시 `get_or_create_current_deployment`
  로 "지금 배포"를 찾아 고정한다(`repository.py` docstring 참고).

`docs/planning/04_인프라_네트워크_클라우드.md`: "이미지 digest, Git commit SHA, migration·
schema·rule 버전을 배포 메타데이터로 등록한다."
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import get_db
from app.modules.deployment.repository import (
    OperationSessionNotFound,
    current_schema_version,
    end_operation_session,
    get_operation_session,
    get_or_create_current_deployment,
    list_deployments,
    list_event_log,
    start_operation_session,
)
from app.modules.deployment.schemas import (
    DeploymentOut,
    EventLogOut,
    OperationSessionOut,
    StartOperationSessionRequest,
)

router = APIRouter(tags=["deployment"])


@router.get("/system/build-info")
def get_build_info() -> dict:
    settings = get_settings()
    return {
        "git_sha": settings.git_sha,
        "image_tag": settings.image_tag,
        "schema_version": current_schema_version(),
    }


@router.get("/deployments", response_model=list[DeploymentOut])
def list_deployments_endpoint(db: Session = Depends(get_db)) -> list[DeploymentOut]:
    return [DeploymentOut.model_validate(d) for d in list_deployments(db)]


@router.post("/operation-sessions", response_model=OperationSessionOut, status_code=201)
def start_operation_session_endpoint(
    body: StartOperationSessionRequest, db: Session = Depends(get_db)
) -> OperationSessionOut:
    # "현재 배포"를 먼저 확정(없으면 생성)한 뒤 그 id로 세션을 고정한다 — 두 호출을
    # 분리해두면(repository.py가 각각 독립 함수) 나중에 "이미 알고 있는 deployment_id로
    # 세션을 시작"하는 경로(예: 8단계 CI/CD 자동 등록)도 그대로 재사용할 수 있다.
    deployment = get_or_create_current_deployment(db)
    session = start_operation_session(db, started_by=body.started_by, deployment_id=deployment.id)
    return OperationSessionOut.model_validate(session)


@router.post("/operation-sessions/{session_id}/end", response_model=OperationSessionOut)
def end_operation_session_endpoint(
    session_id: str, db: Session = Depends(get_db)
) -> OperationSessionOut:
    try:
        session = end_operation_session(db, session_id)
    except OperationSessionNotFound:
        raise HTTPException(status_code=404, detail="operation session not found") from None
    return OperationSessionOut.model_validate(session)


@router.get("/operation-sessions/{session_id}", response_model=OperationSessionOut)
def get_operation_session_endpoint(
    session_id: str, db: Session = Depends(get_db)
) -> OperationSessionOut:
    try:
        session = get_operation_session(db, session_id)
    except OperationSessionNotFound:
        raise HTTPException(status_code=404, detail="operation session not found") from None
    return OperationSessionOut.model_validate(session)


@router.get("/event-log", response_model=list[EventLogOut])
def list_event_log_endpoint(
    operation_session_id: str | None = Query(default=None),
    source_channel: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
) -> list[EventLogOut]:
    """정규화 이벤트 조회. 지금은 재생 엔진이 없어 "최근에 뭐가 기록됐는지" 확인용
    (다음 작은 단위에서 이 endpoint 위에 실제 재생 엔진을 쌓는다 — 한 번에 만들지 않고
    먼저 "조회가 되는" 뼈대부터 검증한다)."""
    entries = list_event_log(
        db,
        operation_session_id=operation_session_id,
        source_channel=source_channel,
        since=since,
        until=until,
        limit=limit,
    )
    return [EventLogOut.model_validate(e) for e in entries]
