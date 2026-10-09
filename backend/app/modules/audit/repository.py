"""감사 로그 기록.

공통 데코레이터/미들웨어 대신 각 모듈이 주요 행위 직후 이 함수를 명시적으로 호출한다 —
호출 지점이 몇 곳 안 되는 규모(임무·구역·명령·경보)에서는 데코레이터로 감추는 것보다
"여기서 감사 로그를 남긴다"가 코드에 그대로 보이는 쪽이 더 읽기 쉽다고 판단했다.

주 작업(임무 생성, 명령 승인 등)과 같은 트랜잭션에 묶지 않고 별도로 커밋한다 — 감사
기록 실패로 주 작업 자체가 실패하면 안 되고, 반대로 주 작업 커밋 직후 곧바로 기록하므로
유실 위험은 매우 작다(완전한 outbox 보장은 아니다 — 알려진 한계로 문서화함).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


def record_audit_event(
    db: Session,
    *,
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    result: str = "SUCCESS",
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result=result,
            detail=detail,
        )
    )
    db.commit()
