"""경보 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`: `alerts`(경보 유형·심각도·근거값·확인 상태).
"미확인 경보에 부분 인덱스"를 그대로 반영한다.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False)
    # BATTERY_LOW | RSSI_LOW | GEOFENCE_BREACH
    alert_type: Mapped[str] = mapped_column(String, nullable=False)
    # WARNING | CRITICAL
    severity: Mapped[str] = mapped_column(String, nullable=False)
    rule_version: Mapped[str] = mapped_column(String, nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # OPEN | ACKNOWLEDGED | RESOLVED
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="OPEN")
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_alerts_asset_status", "asset_id", "status"),
        Index("ix_alerts_open", "asset_id", postgresql_where=text("status = 'OPEN'")),
    )
