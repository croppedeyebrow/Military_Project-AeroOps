"""텔레메트리 관련 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`의 핵심 테이블 중 `assets`,
`telemetry_frames`, `asset_latest_state`를 3단계에서 구현한다. `missions`,
`mission_routes`, `geofences`, `alerts`, `users`, `roles`, `audit_logs`는
5·8단계에서 추가한다.

원본(`telemetry_frames`)은 불변으로 보존하고, 관제 조회 비용을 줄이기 위해
최신 정상 프레임만 `asset_latest_state`에 별도 유지한다.
"""
from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Asset(Base):
    """기체 식별자. 텔레메트리 수신 시 처음 보는 `asset_id`는 자동 등록한다(3단계 MVP)."""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    asset_type: Mapped[str] = mapped_column(String, default="drone", server_default="drone")
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TelemetryFrameRecord(Base):
    """`docs/api/telemetry_frame_dictionary.md`의 TelemetryFrame 원본을 그대로 보존한다.

    중복 판정은 `(asset_id, sequence_no)` 유일 제약으로 데이터베이스가 강제한다
    (`docs/planning/03_데이터베이스_아키텍처.md` "주요 인덱스").
    """

    __tablename__ = "telemetry_frames"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), nullable=False)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True)
    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sequence_no: Mapped[int] = mapped_column(nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude_m: Mapped[float] = mapped_column(Float, nullable=False)
    # 위경도·고도(WGS84, PointZ)를 공간 인덱싱용으로도 보존한다. 값의 단일 진실 공급원은
    # 위 세 컬럼이며, position은 GiST 조회(5단계 지오펜스 등)를 위한 파생 컬럼이다.
    position: Mapped[str | None] = mapped_column(Geometry("POINTZ", srid=4326), nullable=True)

    speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    roll_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    pitch_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    yaw_deg: Mapped[float | None] = mapped_column(Float, nullable=True)

    battery_pct: Mapped[float] = mapped_column(Float, nullable=False)
    rssi_dbm: Mapped[float | None] = mapped_column(Float, nullable=True)
    flight_mode: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("asset_id", "sequence_no", name="uq_telemetry_asset_sequence"),
        Index("ix_telemetry_asset_event_time", "asset_id", event_time.desc()),
        Index("ix_telemetry_position", "position", postgresql_using="gist"),
    )


class AssetLatestState(Base):
    """기체별 최신 '정상' 프레임 1건. `event_time`이 후퇴하는 갱신은 거부한다(역순 정책)."""

    __tablename__ = "asset_latest_state"

    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), primary_key=True)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sequence_no: Mapped[int] = mapped_column(nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    altitude_m: Mapped[float] = mapped_column(Float, nullable=False)
    position: Mapped[str | None] = mapped_column(Geometry("POINTZ", srid=4326), nullable=True)

    speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    roll_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    pitch_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    yaw_deg: Mapped[float | None] = mapped_column(Float, nullable=True)

    battery_pct: Mapped[float] = mapped_column(Float, nullable=False)
    rssi_dbm: Mapped[float | None] = mapped_column(Float, nullable=True)
    flight_mode: Mapped[str | None] = mapped_column(String, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
