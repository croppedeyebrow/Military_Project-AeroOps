"""`/alerts` — 조회·확인·해제.

경보 생성은 사용자 요청이 아니라 telemetry consumer가 규칙 평가 결과로 만든다
(`app/modules/telemetry/consumer.py` 참고) — 여기는 조회·확인·해제만 다룬다.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.modules.alert.repository import (
    AlertNotFound,
    AlertNotOpen,
    acknowledge_alert,
    list_alerts,
    resolve_alert,
)
from app.modules.alert.schemas import AcknowledgeAlertRequest, AlertOut, ResolveAlertRequest
from app.modules.audit.repository import record_audit_event

router = APIRouter(prefix="/alerts", tags=["alert"])


@router.get("", response_model=list[AlertOut])
def list_alerts_endpoint(
    status_filter: str | None = Query(default=None, alias="status"),
    asset_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AlertOut]:
    return list_alerts(db, status=status_filter, asset_id=asset_id)


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert_endpoint(
    alert_id: int, body: AcknowledgeAlertRequest, db: Session = Depends(get_db)
) -> AlertOut:
    try:
        alert = acknowledge_alert(db, alert_id, body.acknowledged_by)
    except AlertNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AlertNotOpen as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    record_audit_event(
        db,
        actor=body.acknowledged_by,
        action="alert.acknowledge",
        target_type="alert",
        target_id=str(alert_id),
    )
    return alert


@router.post("/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert_endpoint(
    alert_id: int, body: ResolveAlertRequest, db: Session = Depends(get_db)
) -> AlertOut:
    try:
        alert = resolve_alert(db, alert_id, body.resolved_by)
    except AlertNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AlertNotOpen as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    record_audit_event(
        db,
        actor=body.resolved_by,
        action="alert.resolve",
        target_type="alert",
        target_id=str(alert_id),
    )
    return alert
