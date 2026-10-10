"""배포(`Deployment`) 등록과 운용 세션(`OperationSession`) 수명주기.

목적: 7단계(`docs/roadmap/07_단계_이력재생_관측성_Day16-18.md`)의 핵심 요구사항은
"장애 시점의 Git SHA/이미지 digest/규칙 버전을 역추적할 수 있어야 한다"는 것이다.
이를 위해서는 (1) "지금 이 코드가 어떤 버전 조합인지"를 `Deployment` row로 등록하고,
(2) 운영자가 관제를 시작하는 "운용 구간"마다 그 시점의 `Deployment`를 고정해 묶어두는
`OperationSession`을 만들어야 한다. 이 두 가지를 이 파일에서 구현한다.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.runtime_state import get_current_deployment_id, get_current_operation_session_id
from app.modules.alert.rules import RULE_VERSION
from app.modules.deployment.models import Deployment, EventLog, OperationSession

# backend/app/modules/deployment/repository.py -> parents[3] == backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[3]


class OperationSessionNotFound(Exception):
    pass


def current_schema_version() -> str | None:
    """alembic migration 스크립트 기준 head revision("코드가 기대하는" 스키마 버전).

    근거: DB에 실제 적용된 버전이 아니라 코드 저장소 기준으로 계산한다 — DB 연결 없이
    계산되므로 DB가 잠깐 내려가 있어도 이 값은 계속 읽을 수 있다(원래
    `GET /system/build-info`에만 있던 로직을 여기로 옮겼다 — 배포 등록 시에도 같은
    계산이 필요해져 중복을 피하려고 공용 함수로 뺐다. 1단계 보정 당시 코드와 동일 로직).
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


def get_or_create_current_deployment(db: Session) -> Deployment:
    """"지금 이 프로세스"에 해당하는 `Deployment` row를 찾거나 새로 만든다.

    목적/근거: `docs/planning/03_데이터베이스_아키텍처.md`는 "배포 레코드는 변경하지
    않고 새 버전으로 추가한다"고 규정한다. 하지만 같은 이미지가 재시작되거나 여러
    인스턴스로 떠도(docker compose restart, 수평 확장) 매번 새 row를 추가하면
    `deployments` 테이블이 "같은 배포"로 중복되고, "이 운용 세션이 어느 배포였는지"
    추적이 오히려 더 헷갈린다. 그래서 (git_sha, image_tag, schema_version, rule_version,
    config_version) 5개 값이 **모두 똑같은 row가 이미 있으면 그걸 재사용**하고, 조합이
    하나라도 다르면(코드 배포·규칙 버전 변경 등) 새 row를 추가한다 — "내용이 바뀌었을
    때만 새 버전"이라는 원칙을 그대로 구현한 것이다.
    """
    settings = get_settings()
    schema_version = current_schema_version()
    # rule_version: 경보 규칙 버전(alert/rules.py). 7단계 시점에는 ML 규칙이 없어
    # 유일한 "규칙 버전"이 이것뿐이다 — AI/MLOps 레이어가 붙으면(V03 보정 백로그)
    # 모델 버전도 여기 합성해 넣을 자리다.
    rule_version = RULE_VERSION
    # config_version: 아직 별도 설정 버전 체계가 없다 — settings 자체가 코드와 함께
    # 배포되는 MVP 구조라 git_sha가 곧 config_version 역할을 겸한다고 보고 None으로 둔다
    # (완전히 분리된 설정 저장소가 생기면 그때 실제 값을 넣는다).
    config_version = None

    existing = db.execute(
        select(Deployment).where(
            Deployment.git_sha == settings.git_sha,
            Deployment.image_tag == settings.image_tag,
            Deployment.schema_version == schema_version,
            Deployment.rule_version == rule_version,
            Deployment.config_version == config_version,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    deployment = Deployment(
        id=f"deploy-{uuid.uuid4().hex[:8]}",
        git_sha=settings.git_sha,
        image_tag=settings.image_tag,
        schema_version=schema_version,
        rule_version=rule_version,
        config_version=config_version,
    )
    db.add(deployment)
    db.commit()
    return deployment


def list_deployments(db: Session, limit: int = 50) -> list[Deployment]:
    """최근 등록된 배포부터 반환한다(운영자가 "최근에 뭐가 바뀌었는지" 확인할 때 쓴다)."""
    return list(
        db.execute(select(Deployment).order_by(Deployment.created_at.desc()).limit(limit)).scalars()
    )


def start_operation_session(
    db: Session, *, started_by: str | None, deployment_id: str
) -> OperationSession:
    """운용 세션을 시작한다 — 이 시점의 `deployment_id`를 세션에 고정한다.

    목적/근거: 세션이 끝날 때까지 이 session row를 다시 읽으면 항상 같은
    `deployment_id`가 나와야 한다(앱이 재시작돼 "현재 배포"가 바뀌어도 이미 시작된
    세션의 참조는 바뀌지 않는다) — 그래야 "이 세션 동안 발생한 이벤트는 이 배포 버전
    기준"이라는 역추적이 깨지지 않는다(`docs/roadmap/작업분해_2단계_8단계.md` 7단계
    완료 기준 "장애 시점 deployment·규칙버전 조회 가능").
    """
    session = OperationSession(
        id=f"opsession-{uuid.uuid4().hex[:8]}",
        deployment_id=deployment_id,
        started_by=started_by,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def end_operation_session(db: Session, session_id: str) -> OperationSession:
    """세션을 종료 상태로 표시한다(`ended_at` 설정) — 재생 화면이 "이 구간은 끝난 세션"
    인지 "아직 진행 중"인지 구분하는 데 쓴다."""
    session = db.get(OperationSession, session_id)
    if session is None:
        raise OperationSessionNotFound(session_id)
    if session.ended_at is None:
        session.ended_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
    return session


def get_operation_session(db: Session, session_id: str) -> OperationSession:
    session = db.get(OperationSession, session_id)
    if session is None:
        raise OperationSessionNotFound(session_id)
    return session


def list_operation_sessions(db: Session, limit: int = 50) -> list[OperationSession]:
    return list(
        db.execute(
            select(OperationSession).order_by(OperationSession.started_at.desc()).limit(limit)
        ).scalars()
    )


def append_event_log(
    db: Session,
    *,
    event_time: datetime,
    stream_sequence: int,
    source_channel: str,
    event_type: str,
    correlation_id: str | None = None,
    payload: dict | None = None,
) -> EventLog:
    """`event_log`에 정규화 이벤트 1건을 추가한다 — 재생 엔진(이후 단위)이 읽을 원재료다.

    목적: `docs/planning/05_데이터엔지니어링_아키텍처.md` "이벤트 재생" — "수신 원본과
    정규화 이벤트를 append-only로 보존한다"/"실제 도착 순서와 이벤트 발생 순서를 모두
    보존하여 지연·역순 현상을 재현한다". 두 가지 순서를 각각 어떻게 담는지가 이 함수의
    핵심 설계 포인트다:
      - **도착(처리) 순서**: 이 테이블의 자동증가 `id`(BigInteger, append-only)가 그대로
        "이 프로세스가 실제로 처리한 순서"를 보장한다 — consumer가 asyncio 단일 루프에서
        순차 처리하므로 삽입 순서 = 처리 순서다. 따로 컬럼을 만들 필요가 없다.
      - **이벤트 발생(event-time) 순서**: `event_time` 컬럼 자체가 "그 일이 실제로 언제
        일어났는지"다. 역순 프레임이 와도 이 값은 원본 타임스탬프를 그대로 담으므로,
        재생 엔진이 `ORDER BY event_time`으로 정렬하면 "진짜 발생 순서"를 복원할 수 있다.
      - `stream_sequence`: 같은 `event_time`(또는 같은 채널 안에서의 순서)에서 동률을
        깨는 보조 키다. 채널마다 의미가 다를 수 있어(텔레메트리는 `sequence_no`, 명령은
        `event_no`) 호출하는 쪽이 "그 채널에서 이미 쓰고 있는 단조증가 값"을 넘겨준다 —
        이 함수가 새로 발급하지 않는다(발급하려면 이 함수가 채널별 상태를 알아야 해서
        책임이 커진다).

    `operation_session_id`/`deployment_id`를 인자로 받지 않고 `runtime_state`에서 직접
    읽는 이유: 호출부(telemetry consumer, command/alert/sync repository) 전부가 매번
    "지금 세션이 뭔지"를 알아내서 넘겨주게 하면 호출부 코드가 전부 한 줄씩 더 길어진다.
    "지금 세션이 뭔지"는 전체 프로세스에 하나뿐인 값이라(앞서 `runtime_state.py`
    docstring 참고) 이 함수 내부에서 읽는 쪽이 호출부를 더 단순하게 만든다.
    """
    entry = EventLog(
        operation_session_id=get_current_operation_session_id(),
        event_time=event_time,
        stream_sequence=stream_sequence,
        source_channel=source_channel,
        event_type=event_type,
        correlation_id=correlation_id,
        deployment_id=get_current_deployment_id(),
        payload=payload,
    )
    db.add(entry)
    # 목적: 호출부가 이미 자신의 트랜잭션(예: process_frame의 commit)을 커밋한 "이후"에
    # 이 함수를 부르게 해서, event_log 기록 실패가 원본 데이터 저장 트랜잭션을 롤백시키지
    # 않도록 한다(event_log는 부가적인 재생용 정보라 핵심 쓰기보다 덜 중요하다 — 3단계의
    # audit_log와 같은 원칙). 그래서 여기서 독립적으로 commit한다.
    db.commit()
    return entry


def list_event_log(
    db: Session,
    *,
    operation_session_id: str | None = None,
    source_channel: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 500,
) -> list[EventLog]:
    """재생 엔진·디버깅용 조회. 정렬 기준이 재생의 핵심이라 명시적으로 고정한다.

    목적/근거: `event_time, stream_sequence, id` 순으로 정렬한다 — "이벤트가 실제로
    발생한 시간" 순이 1차 기준이고(재생의 목적 자체가 이 순서를 보여주는 것), 같은
    `event_time`이면 `stream_sequence`로, 그래도 같으면 `id`(삽입 순서, 즉 도착 순서)로
    동률을 깬다. 이렇게 하면 "이벤트 발생 순서로 재생"이 기본 동작이 된다 — "실제 도착
    순서로 재생"이 필요해지면(V03/V04 보정 단계) `ORDER BY id`만 쓰는 별도 모드를
    추가하면 된다(지금은 아직 그 모드를 요구하는 화면이 없어 만들지 않는다 — YAGNI).
    """
    stmt = select(EventLog).order_by(
        EventLog.event_time, EventLog.stream_sequence, EventLog.id
    )
    if operation_session_id is not None:
        stmt = stmt.where(EventLog.operation_session_id == operation_session_id)
    if source_channel is not None:
        stmt = stmt.where(EventLog.source_channel == source_channel)
    if since is not None:
        stmt = stmt.where(EventLog.event_time >= since)
    if until is not None:
        stmt = stmt.where(EventLog.event_time <= until)
    stmt = stmt.limit(limit)
    return list(db.execute(stmt).scalars())
