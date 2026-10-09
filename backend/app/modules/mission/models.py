"""임무·예정경로·구역 테이블.

`docs/planning/03_데이터베이스_아키텍처.md`: `missions`(임무명·상태·시작·종료 시각),
`mission_routes`(예정 경로 LineStringZ), `geofences`(구역 유형과 Polygon).

좌표는 프론트가 바로 GeoJSON으로 그릴 수 있도록 평문 JSONB로도 저장하고, 공간 질의(구역
이탈 판정 등)를 위해 PostGIS geometry 컬럼도 함께 둔다 — telemetry_frames가 lat/lon과
position(geometry)을 함께 갖는 것과 같은 원칙.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # PLANNED | ACTIVE | COMPLETED | ABORTED
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="PLANNED")
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MissionRoute(Base):
    """임무의 예정 경로. 재계획(replanning)을 append-only로 남긴다 — 최신 것이 현재 경로."""

    __tablename__ = "mission_routes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    mission_id: Mapped[str] = mapped_column(ForeignKey("missions.id"), nullable=False)
    # [[lon, lat, alt_m], ...] — 프론트가 그대로 GeoJSON LineString coordinates로 쓴다.
    waypoints: Mapped[list] = mapped_column(JSONB, nullable=False)
    route: Mapped[Any] = mapped_column(Geometry("LINESTRINGZ", srid=4326), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Geofence(Base):
    __tablename__ = "geofences"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # MISSION | CAUTION | PROHIBITED
    zone_type: Mapped[str] = mapped_column(String, nullable=False)
    # [[lon, lat], ...] 닫힌 링(첫 점 == 마지막 점). 프론트 GeoJSON Polygon coordinates[0].
    polygon: Mapped[list] = mapped_column(JSONB, nullable=False)
    geom: Mapped[Any] = mapped_column(Geometry("POLYGON", srid=4326), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
