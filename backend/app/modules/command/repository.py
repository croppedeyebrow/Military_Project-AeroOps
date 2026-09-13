"""Command 생성 로직: idempotency key 기반 최소 골격.

`docs/planning/02_백엔드_아키텍처.md` "명령 처리 규칙": "상태 전이는 DB 트랜잭션과 outbox
event로 함께 기록한다." 3단계 보정에서는 `CREATED` 이벤트 하나만 기록한다 — 승인·전달·
ACK·실행·취소·timeout 상태 전이는 5단계에서 완성한다.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.command.models import Command, CommandEvent
from app.modules.telemetry.repository import ensure_asset_exists
from app.schemas.command import CommandEnvelope


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
        status="DRAFT",
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

    db.add(
        CommandEvent(
            command_id=command.id,
            event_no=1,
            event_type="CREATED",
            occurred_at=datetime.now(timezone.utc),
            actor=envelope.requested_by,
            detail=envelope.model_dump(mode="json"),
        )
    )
    db.commit()
    db.refresh(command)
    return CommandCreationResult(command=command, is_new=True)
