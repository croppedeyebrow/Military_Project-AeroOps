"""Redis Streams consumer: 원본 저장과 최신 상태 갱신을 비동기로 수행한다.

`docs/planning/02_백엔드_아키텍처.md` 처리 흐름의 STREAM → RULE/SAVE 구간.
단일 FastAPI 프로세스 안의 백그라운드 asyncio task로 실행한다
(ADR 0001의 모듈형 모놀리스 원칙 — 별도 워커 프로세스를 추가하지 않는다).

메시지 처리 실패는 성격에 따라 다르게 다룬다(2026-10-24 변경 — 이전에는 실패해도 항상 XACK해서
DB가 순간 끊긴 때의 프레임이 202를 받고도 영구 유실됐다):
- 영구 실패(payload 없음·계약 위반처럼 재처리해도 같은 결과): dead-letter 스트림에 남기고 XACK.
- 일시 실패(DB 순단 등): XACK하지 않아 pending에 남고, 일정 시간 뒤 XAUTOCLAIM으로 다시 가져와
  재처리한다. 원본 저장이 (asset_id, sequence_no) 유일 제약의 ON CONFLICT라 중복 처리돼도 안전하다.
- 전달 횟수가 MAX_DELIVERIES를 넘으면 dead-letter로 보내 무한 재시도를 막는다.
알려진 한계: 원본 저장 커밋 이후 단계(event_log·경보 판정)에서 실패해 재처리되면, 그 프레임은 이미
저장돼 `is_new=False`로 판정되어 최신 상태 갱신·경보 판정이 다시 일어나지 않는다.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from datetime import datetime, timezone

import redis.asyncio as redis
from pydantic import ValidationError
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError

from app.core.metrics import (
    telemetry_consumer_error_total,
    telemetry_dead_letter_total,
    telemetry_duplicate_total,
    telemetry_processing_latency_seconds,
    telemetry_redelivery_total,
)
from app.core.redis import get_telemetry_redis
from app.core.redis_acl import ensure_channel_acl_users
from app.db.base import SessionLocal
from app.modules.alert.repository import evaluate_and_raise_alerts
from app.modules.alert.schemas import AlertOut
from app.modules.deployment.repository import append_event_log
from app.modules.ingestion.streams import CONSUMER_GROUP, CONSUMER_NAME, TELEMETRY_STREAM
from app.modules.realtime.broadcaster import get_broadcaster
from app.modules.telemetry.repository import get_latest_state, process_frame
from app.modules.telemetry.schemas import frame_from_record
from app.schemas.telemetry import TelemetryFrame

logger = logging.getLogger(__name__)

READ_COUNT = 50
BLOCK_MS = 5000
# Redis 재연결 실패 시 재시도 전 대기 — 재시작 직후 바로 재시도하면 아직 뜨지 않은
# Redis에 계속 몰아쳐 로그만 쌓인다(`run_consumer_loop` 참고).
RECONNECT_BACKOFF_S = 2.0
# 처리 실패로 ACK되지 않은 메시지를 다시 가져오는 규칙. 방금 실패한 메시지를 곧바로 다시 돌리면
# 같은 장애(예: DB 순단)에 또 걸리므로 MIN_IDLE만큼 둔 뒤 재시도한다.
RECLAIM_MIN_IDLE_MS = 10_000
RECLAIM_INTERVAL_S = 5.0
# 전달(처음 읽기 + 재전달) 횟수 상한. 넘으면 dead-letter로 보낸다.
MAX_DELIVERIES = 5
# Telemetry 계정의 ACL 키 패턴(`~<telemetry_stream_name>*`)에 포함되는 이름이어야 쓸 수 있다.
DEAD_LETTER_STREAM = f"{TELEMETRY_STREAM}:dead"


async def ensure_consumer_group(redis_client: redis.Redis | None = None) -> None:
    """소비자 그룹을 만든다. 이미 있으면(BUSYGROUP) 조용히 넘어간다."""
    client = redis_client or get_telemetry_redis()
    try:
        await client.xgroup_create(TELEMETRY_STREAM, CONSUMER_GROUP, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def _handle_message(payload: str) -> list[dict]:
    """동기 DB 작업. 이벤트 루프를 막지 않도록 `asyncio.to_thread`에서 호출된다.

    반환값은 실시간(WS) 브로드캐스트로 그대로 발행할 메시지 목록(`{"type": ...}` dict)이다
    — 최신 상태가 실제로 갱신됐을 때만(중복·역순이면 비어있음) "update" 메시지 하나와,
    새로 발생한 경보 수만큼의 "alert" 메시지를 만든다. DB 세션이 닫히기 전에(ORM
    인스턴스가 detach되기 전에) 전부 직렬화 가능한 형태로 꺼내둔다.
    """
    frame = TelemetryFrame.model_validate_json(payload)
    messages: list[dict] = []
    with SessionLocal() as db:
        is_new, latest_updated = process_frame(db, frame)

        # 목적: 7단계 재생 엔진이 "실제로 무슨 일이 있었는지"(중복·역순 포함)를 그대로
        # 복원할 수 있어야 한다 — 그래서 `is_new`/`latest_updated`와 무관하게 수신된
        # 프레임마다 항상 1건을 남긴다(최신 상태를 바꾼 프레임만 남기면, "역순으로 와서
        # 버려진 데이터가 있었다"는 사실 자체가 재생에서 사라진다).
        # stream_sequence=frame.sequence_no: 텔레메트리 채널에서는 기체가 이미
        # 단조증가로 붙여 보내는 값이라 이 함수가 새로 번호를 매길 필요가 없다
        # (`append_event_log` docstring의 "stream_sequence" 설명 참고).
        append_event_log(
            db,
            event_time=frame.event_time,
            stream_sequence=frame.sequence_no,
            source_channel="telemetry",
            event_type="telemetry.received",
            correlation_id=frame.correlation_id,
            payload={
                "asset_id": frame.asset_id,
                "sequence_no": frame.sequence_no,
                "is_new": is_new,
                "latest_updated": latest_updated,
            },
        )

        if latest_updated:
            latest_record = get_latest_state(db, frame.asset_id)
            if latest_record is not None:
                latest_frame = frame_from_record(latest_record)
                messages.append({"type": "update", "asset": latest_frame.model_dump(mode="json")})

                new_alerts = evaluate_and_raise_alerts(db, latest_frame)
                for alert in new_alerts:
                    alert_out = AlertOut.model_validate(alert).model_dump(mode="json")
                    messages.append({"type": "alert", "alert": alert_out})

    if frame.received_at is not None:
        latency_s = (datetime.now(timezone.utc) - frame.received_at).total_seconds()
        telemetry_processing_latency_seconds.observe(max(0.0, latency_s))
    if not is_new:
        telemetry_duplicate_total.labels(asset_id=frame.asset_id).inc()

    return messages


async def _dead_letter(
    client: redis.Redis, message_id: str, fields: dict, reason: str, deliveries: int
) -> None:
    """처리할 수 없는 메시지를 원본 그대로 dead-letter 스트림에 남기고 ACK한다.

    dead-letter 기록(XADD)이 실패하면 예외가 그대로 올라가 ACK하지 않으므로, 증거를 남기지 못한
    채 메시지를 잃는 일은 없다.
    """
    await client.xadd(
        DEAD_LETTER_STREAM,
        {
            "original_id": message_id,
            "reason": reason,
            "deliveries": str(deliveries),
            "payload": str(fields.get("payload") or ""),
        },
    )
    await client.xack(TELEMETRY_STREAM, CONSUMER_GROUP, message_id)
    telemetry_dead_letter_total.labels(reason=reason).inc()
    logger.error(
        "텔레메트리 메시지를 dead-letter로 이동: message_id=%s reason=%s deliveries=%s",
        message_id,
        reason,
        deliveries,
    )


async def _process_one(
    client: redis.Redis, message_id: str, fields: dict, deliveries: int
) -> None:
    """메시지 1건을 처리한다. 성공·영구 실패는 ACK하고, 일시 실패는 ACK하지 않고 남긴다."""
    payload = fields.get("payload")
    if payload is None:
        await _dead_letter(client, message_id, fields, "missing_payload", deliveries)
        return
    if deliveries > MAX_DELIVERIES:
        await _dead_letter(client, message_id, fields, "max_deliveries", deliveries)
        return
    if deliveries > 1:
        telemetry_redelivery_total.inc()

    try:
        broadcast_messages = await asyncio.to_thread(_handle_message, payload)
    except ValidationError:
        # 깨진 JSON·계약 위반은 다시 처리해도 같은 결과다.
        telemetry_consumer_error_total.inc()
        await _dead_letter(client, message_id, fields, "invalid_payload", deliveries)
        return
    except Exception:  # noqa: BLE001 — 일시 실패로 보고 ACK하지 않는다(재전달 대상)
        telemetry_consumer_error_total.inc()
        logger.exception(
            "텔레메트리 메시지 처리 실패(재전달 예정): message_id=%s deliveries=%s",
            message_id,
            deliveries,
        )
        return

    broadcaster = get_broadcaster()
    for message in broadcast_messages:
        broadcaster.publish(message)
    await client.xack(TELEMETRY_STREAM, CONSUMER_GROUP, message_id)


async def _reclaim_and_process(client: redis.Redis) -> None:
    """ACK되지 않은 채 MIN_IDLE 이상 지난 메시지를 다시 가져와 처리한다."""
    result = await client.xautoclaim(
        TELEMETRY_STREAM,
        CONSUMER_GROUP,
        CONSUMER_NAME,
        min_idle_time=RECLAIM_MIN_IDLE_MS,
        start_id="0-0",
        count=READ_COUNT,
    )
    for message_id, fields in result[1]:
        # XAUTOCLAIM이 전달 횟수를 이미 1 올렸으므로 이 값이 "이번 포함 총 전달 횟수"다.
        pending = await client.xpending_range(
            TELEMETRY_STREAM, CONSUMER_GROUP, min=message_id, max=message_id, count=1
        )
        deliveries = int(pending[0]["times_delivered"]) if pending else 1
        await _process_one(client, message_id, fields or {}, deliveries)


async def run_consumer_loop(redis_client: redis.Redis | None = None) -> None:
    """`CancelledError`(앱 종료)로 멈출 때까지 스트림을 계속 소비한다.

    `xreadgroup`/`xack` 같은 Redis 레벨 호출이 예외를 던지면(기존 코드는 이를 전혀
    잡지 않았다) 이 루프를 감싸는 asyncio task가 그대로 끝나버려, 프로세스가 재시작될
    때까지 텔레메트리 소비가 영구히 멈춘다 — 7단계 장애 시험(2026-10-16)에서 Redis를
    `docker stop`/`start`로 재시작한 뒤 이 상태가 실제로 재현됐다(이 dev compose는
    Redis에 영속 볼륨이 없어, 재시작마다 ACL 사용자·consumer group이 함께 사라진다).
    그래서 루프 본문 전체를 try/except로 감싸, Redis 쪽 예외는 ACL·consumer group을
    재등록하고 계속 돌게 한다 — 메시지 하나의 처리 실패(아래 안쪽 try/except)와는
    별개의 복구 경로다.
    """
    client = redis_client or get_telemetry_redis()
    await ensure_consumer_group(client)

    last_reclaim = 0.0
    while True:
        try:
            if time.monotonic() - last_reclaim >= RECLAIM_INTERVAL_S:
                last_reclaim = time.monotonic()
                await _reclaim_and_process(client)

            response = await client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={TELEMETRY_STREAM: ">"},
                count=READ_COUNT,
                block=BLOCK_MS,
            )
            if not response:
                continue

            for _stream_name, stream_messages in response:
                for message_id, fields in stream_messages:
                    await _process_one(client, message_id, fields, deliveries=1)
        except (RedisConnectionError, ResponseError) as exc:
            telemetry_consumer_error_total.inc()
            logger.warning(
                "Redis 스트림 연결 실패 — ACL·consumer group 재등록 후 재시도: %s", exc
            )
            await asyncio.sleep(RECONNECT_BACKOFF_S)
            with contextlib.suppress(Exception):
                await ensure_channel_acl_users()
                await ensure_consumer_group(client)
