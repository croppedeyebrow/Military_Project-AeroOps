"""배포 추적 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`: `deployments`(Git SHA·image digest·설정·
스키마·규칙 버전), `event_log`(재생 가능한 정규화 도메인 이벤트), `operation_sessions`
(운용 구간과 deployment_id 연결). 3단계 보정에서는 `deployments`/`event_log` 테이블만
먼저 만들었다(값을 채우는 로직은 미구현). 7단계에서 `OperationSession`을 추가하고
실제로 값을 채우기 시작한다 — 아래 각 클래스 docstring 참고.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Deployment(Base):
    """실행 중인 코드·이미지·스키마·규칙 버전 한 세트. 변경하지 않고 새 버전으로 추가한다."""

    __tablename__ = "deployments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    git_sha: Mapped[str] = mapped_column(String, nullable=False)
    image_tag: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str | None] = mapped_column(String, nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String, nullable=True)
    config_version: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OperationSession(Base):
    """"운용 구간" 하나 — 운영자가 관제를 시작한 시점부터 끝낸(또는 아직 끝나지 않은)
    시점까지를 구분하는 단위다.

    왜 필요한가(목적): 장애가 발생했을 때 "그 시점에 정확히 어떤 코드/이미지/규칙
    버전이 돌고 있었는지"를 역추적하려면(`docs/planning/03_데이터베이스_아키텍처.md`
    "이벤트·배포 추적성"), 모든 telemetry/command/alert/sync 이벤트가 "현재 실행 중인
    배포"를 가리키는 고정된 참조점이 있어야 한다. 이벤트마다 그때그때 `Deployment`를
    새로 조회해서 넣으면, 앱이 재시작되는 순간 같은 운용 구간 안에서도 참조가 바뀔 수
    있다 — 그래서 "세션 시작 시점에 현재 deployment_id를 한 번 고정하고, 세션이 끝날
    때까지 그 값을 그대로 쓴다"는 규칙을 테이블로 강제한다(`docs/roadmap/
    07_단계_이력재생_관측성_Day16-18.md` "운용 세션 시작 시 현재 deployment_id를 고정").

    근거(설계 결정): `deployment_id`를 nullable로 두지 않고 required로 만든 이유는
    `docs/planning/03_데이터베이스_아키텍처.md`의 정합성 검증 규칙
    "운용 세션의 deployment_id 필수 연결"을 DB 레벨에서도 지키기 위함이다 — 애플리케이션
    버그로 deployment_id 없이 세션이 생성되는 사고를 막는다.
    """

    __tablename__ = "operation_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    # nullable=False: 위 docstring "근거" 참고 — 세션은 반드시 특정 배포에 묶인다.
    deployment_id: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # null이면 "아직 진행 중인 세션"이라는 뜻 — 별도 상태 컬럼 대신 timestamp의
    # 존재 여부로 표현한다(상태값 하나 추가하는 것보다 더 적은 상태로 같은 의미를 표현).
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_by: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EventLog(Base):
    """append-only 정규화 도메인 이벤트(재생용). 7단계에서 실제로 기록을 시작한다."""

    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operation_session_id: Mapped[str | None] = mapped_column(String, nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stream_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # telemetry | command | alert | sync
    source_channel: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    deployment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "ix_event_log_session_time_seq",
            "operation_session_id",
            "event_time",
            "stream_sequence",
        ),
    )
