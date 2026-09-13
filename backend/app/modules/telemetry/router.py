"""`GET /assets`, `GET /assets/{id}/latest`, `GET /assets/{id}/telemetry` — 최신 상태와
기간별 이력 조회.

동기 SQLAlchemy Session을 쓰지만 route 핸들러를 `def`(sync)로 선언해 FastAPI가
자동으로 스레드풀에서 실행하게 한다 — 이벤트 루프(수집 API, 실시간 처리)를 막지 않는다.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.modules.telemetry.repository import (
    get_all_latest_states,
    get_latest_state,
    get_telemetry_history,
)
from app.modules.telemetry.schemas import TelemetryHistoryResponse, frame_from_record
from app.schemas.telemetry import TelemetryFrame

router = APIRouter(prefix="/assets", tags=["telemetry"])


@router.get("", response_model=list[TelemetryFrame])
def list_assets_latest(db: Session = Depends(get_db)) -> list[TelemetryFrame]:
    """전체 기체의 최신 상태 목록. 프론트가 `/ws/operations` 연결 전 초기 페인트에 쓴다
    (`docs/planning/01_프론트엔드_아키텍처.md`: "TanStack Query로 초기 자산 목록/최신 상태
    조회, WS와 병행"). WS 스냅샷과 같은 데이터를 반환한다.
    """
    return [frame_from_record(r) for r in get_all_latest_states(db)]


@router.get("/{asset_id}/latest", response_model=TelemetryFrame)
def get_asset_latest(asset_id: str, db: Session = Depends(get_db)) -> TelemetryFrame:
    record = get_latest_state(db, asset_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"'{asset_id}'의 최신 상태가 없습니다")
    return frame_from_record(record)


@router.get("/{asset_id}/telemetry", response_model=TelemetryHistoryResponse)
def get_asset_telemetry(
    asset_id: str,
    start: datetime | None = Query(default=None, description="조회 시작(event_time, UTC) 포함"),
    end: datetime | None = Query(default=None, description="조회 종료(event_time, UTC) 포함"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> TelemetryHistoryResponse:
    records = get_telemetry_history(db, asset_id, start=start, end=end, limit=limit, offset=offset)
    items = [frame_from_record(r) for r in records]
    return TelemetryHistoryResponse(
        asset_id=asset_id, limit=limit, offset=offset, count=len(items), items=items
    )
