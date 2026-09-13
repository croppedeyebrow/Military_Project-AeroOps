"""`POST /commands` — 명령 생성(idempotency key 기반 최소 골격).

승인·전달·ACK·취소·타임아웃 상태 머신은 5단계에서 완성한다. 3단계 보정에서는 "같은
idempotency_key로 여러 번 요청해도 명령이 하나만 생성된다"만 보장한다
(`docs/roadmap/작업분해_2단계_8단계.md` "3단계 보정").
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.redis import get_command_redis
from app.db.base import get_db
from app.modules.command.repository import IdempotencyConflict, create_command_idempotent
from app.modules.command.schemas import CommandCreatedResponse
from app.modules.command.streams import COMMAND_STREAM
from app.schemas.command import CommandEnvelope

logger = logging.getLogger(__name__)

router = APIRouter(tags=["command"])


@router.post("/commands", response_model=CommandCreatedResponse)
async def create_command(
    envelope: CommandEnvelope, response: Response, db: Session = Depends(get_db)
) -> CommandCreatedResponse:
    try:
        result = create_command_idempotent(db, envelope)
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    response.status_code = status.HTTP_201_CREATED if result.is_new else status.HTTP_200_OK

    if result.is_new:
        # 커밋된 CREATED 이벤트를 command 채널에도 발행한다 — 실패해도 이미 DB에는
        # durable하게 기록되어 있으므로(위 트랜잭션) 명령 생성 자체를 실패시키지 않는다.
        try:
            redis_client = get_command_redis()
            await redis_client.xadd(
                COMMAND_STREAM,
                {"payload": envelope.model_dump_json(), "event_type": "CREATED"},
            )
        except Exception:  # noqa: BLE001 — 발행 실패가 명령 생성 자체를 실패시키면 안 된다
            logger.exception("command stream 발행 실패: command_id=%s", envelope.command_id)

    return CommandCreatedResponse(
        command_id=result.command.id,
        idempotency_key=result.command.idempotency_key,
        target_asset_id=result.command.target_asset_id,
        command_type=result.command.command_type,
        status=result.command.status,
        created_at=result.command.created_at,
        is_new=result.is_new,
    )
