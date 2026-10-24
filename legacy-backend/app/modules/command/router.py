"""Command API — 생성, 승인/취소, 기체 ACK·실행·결과 보고, 조회.

`docs/planning/00_종합_기획서.md` "명령 수명주기": `DRAFT → PENDING_APPROVAL → APPROVED
→ DISPATCHED → ACKNOWLEDGED → EXECUTING → SUCCEEDED/FAILED/TIMED_OUT/CANCELLED`.
전이 규칙은 `state_machine.py`, DB 작업은 `repository.py` 참고.

승인 즉시(만료 전이면) 자동으로 전달(DISPATCHED)까지 진행하고, 그때 Command Redis
Stream에 발행한다 — 승인되지 않은 명령은 기체가 볼 수 있는 채널에 아예 나타나지 않는다
("승인되지 않았거나 만료된 명령은 전달되지 않는다").
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.redis import get_command_redis
from app.core.redis_acl import xadd_with_acl_retry
from app.db.base import get_db
from app.modules.audit.repository import record_audit_event
from app.modules.command.models import Command
from app.modules.command.repository import (
    CommandNotCancellable,
    CommandNotFound,
    IdempotencyConflict,
    SelfApprovalNotAllowed,
    acknowledge_command,
    approve_and_dispatch,
    cancel_command,
    create_command_idempotent,
    get_command,
    get_command_events,
    list_commands,
    report_command_result,
    start_executing_command,
)
from app.modules.command.schemas import (
    ApproveRequest,
    CancelRequest,
    CommandCreatedResponse,
    CommandDetailResponse,
    CommandStatusResponse,
    ResultRequest,
)
from app.modules.command.state_machine import InvalidTransition
from app.modules.command.streams import COMMAND_STREAM
from app.schemas.command import CommandEnvelope

logger = logging.getLogger(__name__)

router = APIRouter(tags=["command"])


def _status_response(command: Command) -> CommandStatusResponse:
    return CommandStatusResponse(
        command_id=command.id, status=command.status, updated_at=command.updated_at
    )


def _to_detail_response(command: Command, events) -> CommandDetailResponse:
    return CommandDetailResponse(
        command_id=command.id,
        idempotency_key=command.idempotency_key,
        target_asset_id=command.target_asset_id,
        command_type=command.command_type,
        requested_by=command.requested_by,
        approved_by=command.approved_by,
        status=command.status,
        issued_at=command.issued_at,
        expires_at=command.expires_at,
        deployment_id=command.deployment_id,
        created_at=command.created_at,
        updated_at=command.updated_at,
        events=list(events),
    )


@router.post("/commands", response_model=CommandCreatedResponse)
def create_command(
    envelope: CommandEnvelope, response: Response, db: Session = Depends(get_db)
) -> CommandCreatedResponse:
    try:
        result = create_command_idempotent(db, envelope)
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    response.status_code = status.HTTP_201_CREATED if result.is_new else status.HTTP_200_OK

    if result.is_new:
        record_audit_event(
            db,
            actor=envelope.requested_by,
            action="command.create",
            target_type="command",
            target_id=result.command.id,
            detail={
                "command_type": envelope.command_type,
                "target_asset_id": envelope.target_asset_id,
            },
        )

    return CommandCreatedResponse(
        command_id=result.command.id,
        idempotency_key=result.command.idempotency_key,
        target_asset_id=result.command.target_asset_id,
        command_type=result.command.command_type,
        status=result.command.status,
        created_at=result.command.created_at,
        is_new=result.is_new,
    )


@router.get("/commands", response_model=list[CommandStatusResponse])
def list_commands_endpoint(
    status_filter: str | None = Query(default=None, alias="status"),
    target_asset_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CommandStatusResponse]:
    commands = list_commands(db, status=status_filter, target_asset_id=target_asset_id)
    return [
        CommandStatusResponse(command_id=c.id, status=c.status, updated_at=c.updated_at)
        for c in commands
    ]


@router.get("/commands/{command_id}", response_model=CommandDetailResponse)
def get_command_detail(command_id: str, db: Session = Depends(get_db)) -> CommandDetailResponse:
    try:
        command = get_command(db, command_id)
    except CommandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    events = get_command_events(db, command_id)
    return _to_detail_response(command, events)


@router.post("/commands/{command_id}/approve", response_model=CommandStatusResponse)
async def approve_command_endpoint(
    command_id: str, body: ApproveRequest, db: Session = Depends(get_db)
) -> CommandStatusResponse:
    try:
        command = approve_and_dispatch(db, command_id, body.approved_by)
    except CommandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SelfApprovalNotAllowed as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    record_audit_event(
        db,
        actor=body.approved_by,
        action="command.approve",
        target_type="command",
        target_id=command_id,
        detail={"resulting_status": command.status},
    )

    if command.status == "DISPATCHED":
        try:
            redis_client = get_command_redis()
            await xadd_with_acl_retry(
                redis_client,
                COMMAND_STREAM,
                {"command_id": command.id, "event_type": "DISPATCHED"},
            )
        except Exception:  # noqa: BLE001 — 발행 실패가 승인 자체를 실패시키면 안 된다
            logger.exception("command stream 발행 실패: command_id=%s", command_id)

    return _status_response(command)


@router.post("/commands/{command_id}/cancel", response_model=CommandStatusResponse)
def cancel_command_endpoint(
    command_id: str, body: CancelRequest, db: Session = Depends(get_db)
) -> CommandStatusResponse:
    try:
        command = cancel_command(db, command_id, body.cancelled_by, body.reason)
    except CommandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CommandNotCancellable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    record_audit_event(
        db,
        actor=body.cancelled_by,
        action="command.cancel",
        target_type="command",
        target_id=command_id,
        detail={"reason": body.reason},
    )
    return _status_response(command)


@router.post("/commands/{command_id}/ack", response_model=CommandStatusResponse)
def ack_command_endpoint(command_id: str, db: Session = Depends(get_db)) -> CommandStatusResponse:
    try:
        command = acknowledge_command(db, command_id)
    except CommandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _status_response(command)


@router.post("/commands/{command_id}/execute", response_model=CommandStatusResponse)
def execute_command_endpoint(
    command_id: str, db: Session = Depends(get_db)
) -> CommandStatusResponse:
    try:
        command = start_executing_command(db, command_id)
    except CommandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _status_response(command)


@router.post("/commands/{command_id}/result", response_model=CommandStatusResponse)
def report_result_endpoint(
    command_id: str, body: ResultRequest, db: Session = Depends(get_db)
) -> CommandStatusResponse:
    try:
        command = report_command_result(db, command_id, body.outcome, body.detail)
    except CommandNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _status_response(command)
