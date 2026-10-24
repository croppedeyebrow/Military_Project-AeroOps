"""Redis Streams consumer: 원본 저장과 최신 상태 갱신을 비동기로 수행한다.

`docs/planning/02_백엔드_아키텍처.md` 처리 흐름의 STREAM → RULE/SAVE 구간.
단일 FastAPI 프로세스 안의 백그라운드 asyncio task로 실행한다
(ADR 0001의 모듈형 모놀리스 원칙 — 별도 워커 프로세스를 추가하지 않는다).

한 메시지 처리에 실패해도(예: 손상된 payload) 스트림이 멈추지 않도록 항상 XACK한다.
재처리가 필요한 실패는 로그로만 남긴다 — dead-letter 스트림은 MVP 범위 밖이다.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timezone

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import ResponseError

from app.core.metrics import (
    telemetry_consumer_error_total,
    telemetry_duplicate_total,
    telemetry_processing_latency_seconds,
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

    while True:
        try:
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
                    payload = fields.get("payload")
                    try:
                        if payload is not None:
                            broadcast_messages = await asyncio.to_thread(_handle_message, payload)
                            broadcaster = get_broadcaster()
                            for message in broadcast_messages:
                                broadcaster.publish(message)
                    except Exception:  # noqa: BLE001 — 한 메시지 실패로 스트림 전체가 막히면 안 된다
                        telemetry_consumer_error_total.inc()
                        logger.exception("텔레메트리 메시지 처리 실패: message_id=%s", message_id)
                    finally:
                        await client.xack(TELEMETRY_STREAM, CONSUMER_GROUP, message_id)
        except (RedisConnectionError, ResponseError) as exc:
            telemetry_consumer_error_total.inc()
            logger.warning(
                "Redis 스트림 연결 실패 — ACL·consumer group 재등록 후 재시도: %s", exc
            )
            await asyncio.sleep(RECONNECT_BACKOFF_S)
            with contextlib.suppress(Exception):
                await ensure_channel_acl_users()
                await ensure_consumer_group(client)
