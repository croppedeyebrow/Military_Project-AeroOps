"""Mission/Geofence DB 접근 계층."""
from __future__ import annotations

import json

from geoalchemy2.functions import ST_GeomFromGeoJSON
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.mission.models import Geofence, Mission, MissionRoute


class MissionNotFound(Exception):
    pass


def create_mission(
    db: Session, *, mission_id: str, name: str, start_time=None, end_time=None
) -> Mission:
    mission = Mission(id=mission_id, name=name, start_time=start_time, end_time=end_time)
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


def get_mission(db: Session, mission_id: str) -> Mission:
    mission = db.get(Mission, mission_id)
    if mission is None:
        raise MissionNotFound(f"임무 '{mission_id}'를 찾을 수 없다")
    return mission


def list_missions(db: Session) -> list[Mission]:
    stmt = select(Mission).order_by(Mission.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def update_mission(db: Session, mission_id: str, updates: dict) -> Mission:
    """`updates`에 실제로 들어있는 필드만 갱신한다(부분 갱신, PATCH 의미론).

    라우터가 `MissionUpdateRequest.model_dump(exclude_unset=True)`로 만들어 넘긴다 —
    그래야 "필드를 안 보냄"과 "명시적으로 null로 보냄"(예: `end_time`을 지움)을
    구분할 수 있다.
    """
    mission = get_mission(db, mission_id)
    for field, value in updates.items():
        setattr(mission, field, value)
    db.commit()
    db.refresh(mission)
    return mission


def _line_geojson(waypoints: list[list[float]]) -> str:
    return json.dumps({"type": "LineString", "coordinates": waypoints})


def set_mission_route(db: Session, mission_id: str, waypoints: list[list[float]]) -> MissionRoute:
    get_mission(db, mission_id)  # 존재 확인(없으면 MissionNotFound)
    route = MissionRoute(
        mission_id=mission_id,
        waypoints=waypoints,
        route=ST_GeomFromGeoJSON(_line_geojson(waypoints)),
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


def get_current_route(db: Session, mission_id: str) -> MissionRoute | None:
    stmt = (
        select(MissionRoute)
        .where(MissionRoute.mission_id == mission_id)
        .order_by(MissionRoute.recorded_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _polygon_geojson(polygon: list[list[float]]) -> str:
    return json.dumps({"type": "Polygon", "coordinates": [polygon]})


def create_geofence(
    db: Session, *, geofence_id: str, name: str, zone_type: str, polygon: list[list[float]]
) -> Geofence:
    geofence = Geofence(
        id=geofence_id,
        name=name,
        zone_type=zone_type,
        polygon=polygon,
        geom=ST_GeomFromGeoJSON(_polygon_geojson(polygon)),
    )
    db.add(geofence)
    db.commit()
    db.refresh(geofence)
    return geofence


def list_geofences(db: Session) -> list[Geofence]:
    stmt = select(Geofence).order_by(Geofence.created_at.desc())
    return list(db.execute(stmt).scalars().all())
