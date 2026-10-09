"""`/missions`, `/geofences` — 임무·예정경로·구역 CRUD.

`docs/planning/02_백엔드_아키텍처.md` API 범위: "`/missions`: 임무 CRUD와 상태 변경",
"`/geofences`: 공간 구역 관리".
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.modules.audit.repository import record_audit_event
from app.modules.mission.repository import (
    MissionNotFound,
    create_geofence,
    create_mission,
    get_current_route,
    get_mission,
    list_geofences,
    list_missions,
    set_mission_route,
    update_mission,
)
from app.modules.mission.schemas import (
    GeofenceCreateRequest,
    GeofenceOut,
    MissionCreateRequest,
    MissionOut,
    MissionUpdateRequest,
    RouteOut,
    RouteSetRequest,
)

router = APIRouter(tags=["mission"])

# TODO(8단계): 실제 사용자 인증이 붙기 전까지는 요청자를 이렇게 고정한다.
_UNAUTHENTICATED_ACTOR = "operator"


@router.post("/missions", response_model=MissionOut, status_code=201)
def create_mission_endpoint(
    body: MissionCreateRequest, db: Session = Depends(get_db)
) -> MissionOut:
    mission_id = f"mission-{uuid.uuid4().hex[:8]}"
    mission = create_mission(
        db,
        mission_id=mission_id,
        name=body.name,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    record_audit_event(
        db,
        actor=_UNAUTHENTICATED_ACTOR,
        action="mission.create",
        target_type="mission",
        target_id=mission.id,
        detail={"name": mission.name},
    )
    return mission


@router.get("/missions", response_model=list[MissionOut])
def list_missions_endpoint(db: Session = Depends(get_db)) -> list[MissionOut]:
    return list_missions(db)


@router.get("/missions/{mission_id}", response_model=MissionOut)
def get_mission_endpoint(mission_id: str, db: Session = Depends(get_db)) -> MissionOut:
    try:
        return get_mission(db, mission_id)
    except MissionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/missions/{mission_id}", response_model=MissionOut)
def update_mission_endpoint(
    mission_id: str, body: MissionUpdateRequest, db: Session = Depends(get_db)
) -> MissionOut:
    updates = body.model_dump(exclude_unset=True)
    try:
        mission = update_mission(db, mission_id, updates)
    except MissionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        db,
        actor=_UNAUTHENTICATED_ACTOR,
        action="mission.update",
        target_type="mission",
        target_id=mission_id,
        detail=updates,
    )
    return mission


@router.put("/missions/{mission_id}/route", response_model=RouteOut, status_code=201)
def set_mission_route_endpoint(
    mission_id: str, body: RouteSetRequest, db: Session = Depends(get_db)
) -> RouteOut:
    try:
        route = set_mission_route(db, mission_id, body.waypoints)
    except MissionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_audit_event(
        db,
        actor=_UNAUTHENTICATED_ACTOR,
        action="mission.set_route",
        target_type="mission",
        target_id=mission_id,
        detail={"point_count": len(body.waypoints)},
    )
    return route


@router.get("/missions/{mission_id}/route", response_model=RouteOut)
def get_mission_route_endpoint(mission_id: str, db: Session = Depends(get_db)) -> RouteOut:
    get_mission(db, mission_id)  # 404 처리 재사용
    route = get_current_route(db, mission_id)
    if route is None:
        raise HTTPException(status_code=404, detail=f"임무 '{mission_id}'의 예정 경로가 없다")
    return route


@router.post("/geofences", response_model=GeofenceOut, status_code=201)
def create_geofence_endpoint(
    body: GeofenceCreateRequest, db: Session = Depends(get_db)
) -> GeofenceOut:
    geofence = create_geofence(
        db, geofence_id=body.id, name=body.name, zone_type=body.zone_type, polygon=body.polygon
    )
    record_audit_event(
        db,
        actor=_UNAUTHENTICATED_ACTOR,
        action="geofence.create",
        target_type="geofence",
        target_id=geofence.id,
        detail={"zone_type": geofence.zone_type},
    )
    return geofence


@router.get("/geofences", response_model=list[GeofenceOut])
def list_geofences_endpoint(db: Session = Depends(get_db)) -> list[GeofenceOut]:
    return list_geofences(db)
