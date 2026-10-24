"""Command 관련 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`: `commands`(요청자·대상·payload hash·만료·
현재 상태), `command_events`(승인·전달·ACK·실행·취소·timeout 이력). 상태 전이 검증과
timeout worker는 5단계에서 완성한다 — 3단계 보정에서는 idempotency key 기반 최소 생성
골격만 구현한다(`repository.py` 참고).

`Command`가 원본(`CommandEnvelope`)의 실제 `payload`를 그대로 들고 있지 않고
`payload_hash`만 저장하는 이유: 이 테이블은 "현재 상태 스냅샷"이고, 전체 내용(재생·감사용)은
`command_events`의 `CREATED` 이벤트가 `detail`로 보존한다(telemetry의
`telemetry_frames`(원본) vs `asset_latest_state`(최신 요약) 구조와 같은 원칙).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Command(Base):
    """명령 한 건의 현재 상태 스냅샷."""

    __tablename__ = "commands"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # CommandEnvelope.command_id
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    target_asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False)
    command_type: Mapped[str] = mapped_column(String, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False)

    requested_by: Mapped[str] = mapped_column(String, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    expected_asset_state_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deployment_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # DRAFT|PENDING_APPROVAL|APPROVED|DISPATCHED|ACKNOWLEDGED|EXECUTING|
    # SUCCEEDED|FAILED|TIMED_OUT|CANCELLED — 전이 검증은 5단계에서 추가한다.
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="DRAFT")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_commands_target_status_expires", "target_asset_id", "status", "expires_at"),
    )


class CommandEvent(Base):
    """명령 상태 이력(append-only). `event_no`는 명령별로 1부터 단조 증가한다."""

    __tablename__ = "command_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    command_id: Mapped[str] = mapped_column(ForeignKey("commands.id"), nullable=False)
    event_no: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str | None] = mapped_column(String, nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        UniqueConstraint("command_id", "event_no", name="uq_command_events_command_event_no"),
        Index("ix_command_events_command_occurred", "command_id", "occurred_at", "event_no"),
    )
