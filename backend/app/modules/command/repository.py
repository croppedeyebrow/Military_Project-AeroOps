"""Command 생성·상태 전이 로직.

`docs/planning/02_백엔드_아키텍처.md` "명령 처리 규칙": "상태 전이는 DB 트랜잭션과 outbox
event로 함께 기록한다." 상태 그래프 자체는 `state_machine.py`에 있다.

`POST /commands`(생성)는 이미 승인을 구하는 완전한 요청이므로 `DRAFT`를 건너뛰고 곧바로
`PENDING_APPROVAL`로 생성한다(`state_machine.py` docstring 참고).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.metrics import command_created_total, command_status_transition_total
from app.modules.command.models import Command, CommandEvent
from app.modules.command.state_machine import CANCELLABLE_STATUSES, assert_transition_allowed
from app.modules.deployment.repository import append_event_log
from app.modules.telemetry.repository import ensure_asset_exists
from app.schemas.command import CommandEnvelope


class CommandNotFound(Exception):
    pass


class SelfApprovalNotAllowed(Exception):
    """요청자와 승인자를 분리한다(안전한 명령 UX)."""


class CommandNotCancellable(Exception):
    pass


def hash_payload(payload: dict[str, Any]) -> str:
    """payload를 정규화(키 정렬)한 뒤 SHA-256 해시한다 — 동일 내용은 항상 같은 해시.

    `commands` 테이블은 전체 payload가 아니라 이 해시만 보관한다(모델 docstring 참고).
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyConflict(Exception):
    """같은 idempotency_key가 다른 내용(command_id 또는 payload)으로 재사용됐다."""


@dataclass(frozen=True)
class CommandCreationResult:
    command: Command
    is_new: bool  # False면 기존 명령을 멱등하게 반환한 것 — 재실행이 아니다.


def _get_by_idempotency_key(db: Session, idempotency_key: str) -> Command | None:
    return db.execute(
        select(Command).where(Command.idempotency_key == idempotency_key)
    ).scalar_one_or_none()


def _reconcile_existing(
    existing: Command, envelope: CommandEnvelope, payload_hash: str
) -> CommandCreationResult:
    if existing.id != envelope.command_id or existing.payload_hash != payload_hash:
        raise IdempotencyConflict(
            f"idempotency_key '{envelope.idempotency_key}'가 다른 명령에 이미 쓰였다"
        )
    return CommandCreationResult(command=existing, is_new=False)


def create_command_idempotent(db: Session, envelope: CommandEnvelope) -> CommandCreationResult:
    """idempotency_key로 명령을 멱등 생성한다.

    - 같은 idempotency_key + 같은 payload로 재요청 → 기존 명령을 그대로 반환한다(재실행 아님).
    - 같은 idempotency_key인데 내용이 다르면 → 키 오용으로 간주해 `IdempotencyConflict`.
    - 동시 요청으로 유일 제약이 걸리는 경우도(경쟁 상태) 예외를 잡아 같은 방식으로 처리한다.
    """
    ensure_asset_exists(db, envelope.target_asset_id)
    payload_hash = hash_payload(envelope.payload)

    existing = _get_by_idempotency_key(db, envelope.idempotency_key)
    if existing is not None:
        return _reconcile_existing(existing, envelope, payload_hash)

    command = Command(
        id=envelope.command_id,
        idempotency_key=envelope.idempotency_key,
        target_asset_id=envelope.target_asset_id,
        command_type=envelope.command_type,
        payload_hash=payload_hash,
        requested_by=envelope.requested_by,
        approved_by=envelope.approved_by,
        issued_at=envelope.issued_at,
        expires_at=envelope.expires_at,
        expected_asset_state_version=envelope.expected_asset_state_version,
        deployment_id=envelope.deployment_id,
        status="PENDING_APPROVAL",
    )
    db.add(command)
    try:
        db.flush()  # command_events.command_id FK가 참조할 수 있도록 먼저 반영
    except IntegrityError:
        db.rollback()
        existing = _get_by_idempotency_key(db, envelope.idempotency_key)
        if existing is None:
            raise  # idempotency_key 충돌이 아닌 다른 무결성 오류 — 그대로 알린다
        return _reconcile_existing(existing, envelope, payload_hash)

    created_at = datetime.now(timezone.utc)
    db.add(
        CommandEvent(
            command_id=command.id,
            event_no=1,
            event_type="CREATED",
            occurred_at=created_at,
            actor=envelope.requested_by,
            detail=envelope.model_dump(mode="json"),
        )
    )
    db.commit()
    db.refresh(command)

    # 목적: event_log는 "재생 가능한 정규화 이벤트"의 전체 집합이어야 한다(텔레메트리만
    # 있고 명령이 빠지면 재생 화면에서 "그때 승인된 명령"을 못 보여준다). commit 이후에
    # 불러서 commands/command_events 쓰기 트랜잭션에 영향이 없게 한다(telemetry
    # consumer에서와 같은 원칙).
    # correlation_id=command.id: CommandEnvelope엔 별도 correlation_id 필드가 없다 —
    # "이 명령에 관한 모든 이벤트를 하나로 묶는 키"로 command_id 자체가 이미 그 역할을
    # 하므로 새 필드를 추가하지 않고 재사용한다.
    append_event_log(
        db,
        event_time=created_at,
        stream_sequence=1,
        source_channel="command",
        event_type="command.CREATED",
        correlation_id=command.id,
        payload={"command_id": command.id, "target_asset_id": command.target_asset_id},
    )
    # event_log와 같은 이유로 commit 이후에 집계한다 — 메트릭 기록 실패가 명령 생성
    # 자체를 롤백시키면 안 된다(실제로 prometheus_client의 Counter.inc()는 거의 실패하지
    # 않지만, "핵심 쓰기 트랜잭션 vs 부가 관측 기록"의 순서 원칙은 일관되게 지킨다).
    command_created_total.labels(command_type=envelope.command_type).inc()
    return CommandCreationResult(command=command, is_new=True)


def get_command(db: Session, command_id: str) -> Command:
    command = db.get(Command, command_id)
    if command is None:
        raise CommandNotFound(f"명령 '{command_id}'을 찾을 수 없다")
    return command


def get_command_events(db: Session, command_id: str) -> list[CommandEvent]:
    stmt = (
        select(CommandEvent)
        .where(CommandEvent.command_id == command_id)
        .order_by(CommandEvent.event_no.asc())
    )
    return list(db.execute(stmt).scalars().all())


def list_commands(
    db: Session, *, status: str | None = None, target_asset_id: str | None = None
) -> list[Command]:
    stmt = select(Command)
    if status is not None:
        stmt = stmt.where(Command.status == status)
    if target_asset_id is not None:
        stmt = stmt.where(Command.target_asset_id == target_asset_id)
    stmt = stmt.order_by(Command.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def _next_event_no(db: Session, command_id: str) -> int:
    current_max = db.execute(
        select(func.max(CommandEvent.event_no)).where(CommandEvent.command_id == command_id)
    ).scalar_one_or_none()
    return (current_max or 0) + 1


def _transition(
    db: Session,
    command: Command,
    target: str,
    *,
    actor: str | None,
    detail: dict[str, Any] | None = None,
) -> Command:
    """상태를 바꾸고 같은 이벤트를 `command_events`에 남긴다. `event_type`은 목표 상태와
    같은 이름을 쓴다(예: `APPROVED` 상태로 가면 `APPROVED` 이벤트) — 이력 자체가 상태
    변화 로그이기 때문이다.
    """
    assert_transition_allowed(command.status, target)
    command.status = target
    event_no = _next_event_no(db, command.id)
    occurred_at = datetime.now(timezone.utc)
    db.add(
        CommandEvent(
            command_id=command.id,
            event_no=event_no,
            event_type=target,
            occurred_at=occurred_at,
            actor=actor,
            detail=detail,
        )
    )
    db.commit()
    db.refresh(command)

    # stream_sequence=event_no: command_events가 이미 명령별로 1부터 매기는 단조증가
    # 값이라(모델 docstring) 그대로 재사용한다 — create_command_idempotent의 CREATED
    # 이벤트와 같은 원칙.
    append_event_log(
        db,
        event_time=occurred_at,
        stream_sequence=event_no,
        source_channel="command",
        event_type=f"command.{target}",
        correlation_id=command.id,
        payload={
            "command_id": command.id,
            "target_asset_id": command.target_asset_id,
            "actor": actor,
        },
    )
    command_status_transition_total.labels(status=target).inc()
    return command


def approve_and_dispatch(db: Session, command_id: str, approved_by: str) -> Command:
    """승인하고, 아직 만료 전이면 곧바로 전달(DISPATCHED)까지 진행한다.

    이 프로젝트에는 사람이 개입하는 별도 "전달" 단계가 없다 — 승인되면 자동으로
    전달된다. 승인 시점에 이미 만료됐다면 전달하지 않고 바로 TIMED_OUT으로 보낸다
    ("만료된 명령은 dispatch하지 않는다").
    """
    command = get_command(db, command_id)
    if command.requested_by == approved_by:
        raise SelfApprovalNotAllowed("요청자 본인은 자신의 명령을 승인할 수 없다")

    now = datetime.now(timezone.utc)
    if now > command.expires_at:
        return _transition(
            db, command, "TIMED_OUT", actor="system", detail={"reason": "expired_before_approval"}
        )

    command.approved_by = approved_by
    command = _transition(db, command, "APPROVED", actor=approved_by)

    now = datetime.now(timezone.utc)
    if now > command.expires_at:
        return _transition(
            db, command, "TIMED_OUT", actor="system", detail={"reason": "expired_before_dispatch"}
        )
    return _transition(db, command, "DISPATCHED", actor="system")


def cancel_command(db: Session, command_id: str, cancelled_by: str, reason: str | None) -> Command:
    command = get_command(db, command_id)
    if command.status not in CANCELLABLE_STATUSES:
        raise CommandNotCancellable(f"'{command.status}' 상태의 명령은 취소할 수 없다")
    detail = {"reason": reason} if reason else None
    return _transition(db, command, "CANCELLED", actor=cancelled_by, detail=detail)


def acknowledge_command(db: Session, command_id: str) -> Command:
    """기체가 명령 수신을 ACK한다(DISPATCHED → ACKNOWLEDGED)."""
    command = get_command(db, command_id)
    return _transition(db, command, "ACKNOWLEDGED", actor="device")


def start_executing_command(db: Session, command_id: str) -> Command:
    command = get_command(db, command_id)
    return _transition(db, command, "EXECUTING", actor="device")


def report_command_result(
    db: Session, command_id: str, outcome: str, detail: dict[str, Any] | None = None
) -> Command:
    """기체가 실행 결과를 보고한다. `outcome`은 `SUCCEEDED` 또는 `FAILED`."""
    command = get_command(db, command_id)
    return _transition(db, command, outcome, actor="device", detail=detail)


def force_timeout(db: Session, command: Command, reason: str = "expired") -> Command:
    """timeout worker가 기한을 넘긴 비종결 명령을 강제로 TIMED_OUT 처리할 때 쓴다."""
    was_status = command.status
    detail = {"reason": reason, "was_status": was_status}
    return _transition(db, command, "TIMED_OUT", actor="system", detail=detail)
