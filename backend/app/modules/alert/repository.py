"""Alert DB 접근 계층 — 생성(중복 방지)·확인·해제·조회."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.alert.models import Alert
from app.modules.alert.rules import RULE_VERSION, evaluate_all
from app.modules.mission.repository import list_geofences
from app.schemas.telemetry import TelemetryFrame


class AlertNotFound(Exception):
    pass


class AlertNotOpen(Exception):
    """이미 확인/해제된 경보에 다시 확인/해제를 시도했다."""


def get_open_alert(db: Session, asset_id: str, alert_type: str) -> Alert | None:
    stmt = select(Alert).where(
        Alert.asset_id == asset_id, Alert.alert_type == alert_type, Alert.status == "OPEN"
    )
    return db.execute(stmt).scalars().first()


def evaluate_and_raise_alerts(db: Session, frame: TelemetryFrame) -> list[Alert]:
    """프레임을 규칙에 대입해 새 경보를 만든다.

    같은 asset_id+alert_type의 `OPEN` 경보가 이미 있으면 새로 만들지 않는다 — 배터리가
    낮은 상태가 계속돼도(수십~수백 프레임) 경보가 프레임마다 새로 쌓이지 않게 한다.
    """
    geofences = list_geofences(db)
    candidates = evaluate_all(frame, geofences)

    created: list[Alert] = []
    for candidate in candidates:
        if get_open_alert(db, frame.asset_id, candidate.alert_type) is not None:
            continue
        alert = Alert(
            asset_id=frame.asset_id,
            alert_type=candidate.alert_type,
            severity=candidate.severity,
            rule_version=RULE_VERSION,
            evidence=candidate.evidence,
            status="OPEN",
            triggered_at=frame.event_time,
        )
        db.add(alert)
        created.append(alert)

    if created:
        db.commit()
        for alert in created:
            db.refresh(alert)
    return created


def get_alert(db: Session, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise AlertNotFound(f"경보 #{alert_id}를 찾을 수 없다")
    return alert


def list_alerts(
    db: Session, *, status: str | None = None, asset_id: str | None = None
) -> list[Alert]:
    stmt = select(Alert)
    if status is not None:
        stmt = stmt.where(Alert.status == status)
    if asset_id is not None:
        stmt = stmt.where(Alert.asset_id == asset_id)
    stmt = stmt.order_by(Alert.triggered_at.desc())
    return list(db.execute(stmt).scalars().all())


def acknowledge_alert(db: Session, alert_id: int, acknowledged_by: str) -> Alert:
    alert = get_alert(db, alert_id)
    if alert.status != "OPEN":
        raise AlertNotOpen(f"경보 #{alert_id}는 이미 '{alert.status}' 상태다")
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = acknowledged_by
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(db: Session, alert_id: int, resolved_by: str) -> Alert:
    alert = get_alert(db, alert_id)
    if alert.status == "RESOLVED":
        raise AlertNotOpen(f"경보 #{alert_id}는 이미 해제됐다")
    alert.status = "RESOLVED"
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = resolved_by
    db.commit()
    db.refresh(alert)
    return alert
