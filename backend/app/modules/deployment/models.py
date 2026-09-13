"""배포 추적 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`: `deployments`(Git SHA·image digest·설정·
스키마·규칙 버전), `event_log`(재생 가능한 정규화 도메인 이벤트). 3단계 보정에서 테이블만
만든다 — 실제로 값을 채우는 로직(배포 자동 등록은 8단계, 이벤트 재생은 7단계)은 이후에
구현한다.
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
