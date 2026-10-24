"""Deployment/OperationSession API.

- `GET /system/build-info`: 1단계 보정에서 만든 최소 endpoint. "지금 이 프로세스가 어떤
  버전인지"를 DB 연결 없이 바로 확인한다(`app/modules/deployment/repository.py`의
  `current_schema_version()`을 그대로 쓴다 — DB 조회 없이 alembic head만 읽는 그 함수).
- `GET /deployments`: 7단계에서 추가. `deployments` row 목록(최근 등록 순) — 운영자가
  "최근에 뭐가 바뀌었는지" 확인하거나, 재생 화면에서 특정 배포를 선택할 때 쓴다.
- `GET /deployments/{id}`: 특정 배포 단건 조회(`DeploymentBadge`의 "재생 대상" 모드처럼
  `deployment_id` 하나를 사람이 읽을 수 있는 버전 정보로 바꿀 때 쓴다).
- `POST /operation-sessions` / `GET /operation-sessions` / `POST
  /operation-sessions/{id}/end` / `GET /operation-sessions/{id}`: 운용 구간 수명주기.
  시작 시 `get_or_create_current_deployment`로 "지금 배포"를 찾아 고정한다
  (`repository.py` docstring 참고). 목록은 `ReplayTimeline`의 세션 선택 UI가 쓴다.
- `GET /operation-sessions/{id}/replay`: 7단계 재생 엔진 1차 — 세션 메타데이터 +
  정렬된 이벤트 목록(`repository.get_replay_session` docstring 참고). 왜 실제 Command
  채널로 새지 않는지도 그 docstring에 근거를 남겼다(이 endpoint는 조회만 한다).

`docs/planning/04_인프라_네트워크_클라우드.md`: "이미지 digest, Git commit SHA, migration·
schema·rule 버전을 배포 메타데이터로 등록한다."
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import get_db
from app.modules.deployment.repository import (
    DeploymentNotFound,
    EventLogOrder,
    OperationSessionNotFound,
    current_schema_version,
    end_operation_session,
    get_deployment,
    get_operation_session,
    get_or_create_current_deployment,
    get_replay_session,
    list_deployments,
    list_event_log,
    list_operation_sessions,
    start_operation_session,
)
from app.modules.deployment.schemas import (
    DeploymentOut,
    EventLogOut,
    OperationSessionOut,
    ReplaySessionOut,
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


@router.get("/deployments/{deployment_id}", response_model=DeploymentOut)
def get_deployment_endpoint(deployment_id: str, db: Session = Depends(get_db)) -> DeploymentOut:
    try:
        deployment = get_deployment(db, deployment_id)
    except DeploymentNotFound:
        raise HTTPException(status_code=404, detail="deployment not found") from None
    return DeploymentOut.model_validate(deployment)


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


@router.get("/operation-sessions", response_model=list[OperationSessionOut])
def list_operation_sessions_endpoint(
    limit: int = Query(default=50, le=200), db: Session = Depends(get_db)
) -> list[OperationSessionOut]:
    """최근 시작된 세션부터 반환한다 — `ReplayTimeline`이 "재생할 구간"을 고를 때 쓴다."""
    return [OperationSessionOut.model_validate(s) for s in list_operation_sessions(db, limit=limit)]


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
    order: EventLogOrder = Query(
        default="event_time", description="event_time(발생 순서, 기본) | arrival(도착 순서)"
    ),
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db),
) -> list[EventLogOut]:
    """정규화 이벤트 조회(채널·세션을 가로지르는 범용 조회). 세션 단위 재생은
    `GET /operation-sessions/{id}/replay`를 쓴다 — 이 endpoint는 디버깅·채널별 확인처럼
    "특정 세션에 묶이지 않는" 조회에 쓴다."""
    entries = list_event_log(
        db,
        operation_session_id=operation_session_id,
        source_channel=source_channel,
        since=since,
        until=until,
        order=order,
        limit=limit,
    )
    return [EventLogOut.model_validate(e) for e in entries]


@router.get("/operation-sessions/{session_id}/replay", response_model=ReplaySessionOut)
def get_replay_session_endpoint(
    session_id: str,
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    order: EventLogOrder = Query(
        default="event_time", description="event_time(발생 순서, 기본) | arrival(도착 순서)"
    ),
    limit: int = Query(default=2000, le=5000),
    db: Session = Depends(get_db),
) -> ReplaySessionOut:
    try:
        session, events = get_replay_session(
            db, session_id, since=since, until=until, order=order, limit=limit
        )
    except OperationSessionNotFound:
        raise HTTPException(status_code=404, detail="operation session not found") from None
    return ReplaySessionOut(
        session=OperationSessionOut.model_validate(session),
        order=order,
        events=[EventLogOut.model_validate(e) for e in events],
    )
