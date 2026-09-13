"""재동기화(Sync) 세션 기록.

`docs/planning/03_데이터베이스_아키텍처.md`: `sync_sessions`(단절 전후 sequence·snapshot·
조정 결과). 재연결마다 한 행씩 append-only로 쌓는다 — 판단 근거를 항상 감사할 수 있어야
한다(`docs/planning/05_데이터엔지니어링_아키텍처.md` "재동기화 데이터 규칙").
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncSession(Base):
    __tablename__ = "sync_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    reported_last_sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    server_last_sequence_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sequence_gap_count: Mapped[int] = mapped_column(Integer, nullable=False)

    reported_last_processed_command_id: Mapped[str | None] = mapped_column(String, nullable=True)
    pending_command_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    snapshot_reissued: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_sync_sessions_asset_created", "asset_id", "created_at"),)
