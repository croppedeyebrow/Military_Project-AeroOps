"""감사 로그 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`: `audit_logs`(행위자·행동·대상·결과·시각).
append-only — 절대 수정·삭제하지 않는다.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # 예: "mission.create"
    target_type: Mapped[str] = mapped_column(String, nullable=False)  # 예: "mission"
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False, server_default="SUCCESS")
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_audit_logs_target", "target_type", "target_id", "occurred_at"),)
