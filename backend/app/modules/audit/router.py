"""`GET /audit-logs` — 감사 로그 조회(운영자·분석자용, 인증은 8단계에서 적용)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    target_type: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    stmt = select(AuditLog)
    if target_type is not None:
        stmt = stmt.where(AuditLog.target_type == target_type)
    if target_id is not None:
        stmt = stmt.where(AuditLog.target_id == target_id)
    stmt = stmt.order_by(AuditLog.occurred_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all())
