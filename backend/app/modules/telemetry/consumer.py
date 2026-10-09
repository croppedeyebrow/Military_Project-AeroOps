"""Redis Streams consumer: 원본 저장과 최신 상태 갱신을 비동기로 수행한다.

`docs/planning/02_백엔드_아키텍처.md` 처리 흐름의 STREAM → RULE/SAVE 구간.
단일 FastAPI 프로세스 안의 백그라운드 asyncio task로 실행한다
(ADR 0001의 모듈형 모놀리스 원칙 — 별도 워커 프로세스를 추가하지 않는다).

한 메시지 처리에 실패해도(예: 손상된 payload) 스트림이 멈추지 않도록 항상 XACK한다.
재처리가 필요한 실패는 로그로만 남긴다 — dead-letter 스트림은 MVP 범위 밖이다.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import redis.asyncio as redis
from redis.exceptions import ResponseError

from app.core.metrics import (
    telemetry_consumer_error_total,
    telemetry_duplicate_total,
    telemetry_processing_latency_seconds,
)
from app.core.redis import get_telemetry_redis
from app.db.base import SessionLocal
from app.modules.alert.repository import evaluate_and_raise_alerts
from app.modules.alert.schemas import AlertOut
from app.modules.ingestion.streams import CONSUMER_GROUP, CONSUMER_NAME, TELEMETRY_STREAM
from app.modules.realtime.broadcaster import get_broadcaster
from app.modules.telemetry.repository import get_latest_state, process_frame
from app.modules.telemetry.schemas import frame_from_record
from app.schemas.telemetry import TelemetryFrame

logger = logging.getLogger(__name__)

READ_COUNT = 50
BLOCK_MS = 5000


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
    """`CancelledError`(앱 종료)로 멈출 때까지 스트림을 계속 소비한다."""
    client = redis_client or get_telemetry_redis()
    await ensure_consumer_group(client)

    while True:
        response = await client.xreadgroup(
            groupname=CONSUMER_GROUP,
            consumername=CONSUMER_NAME,
            streams={TELEMETRY_STREAM: ">"},
            count=READ_COUNT,
            block=BLOCK_MS,
        )
        if not response:
            continue

        for _stream_name, messages in response:
            for message_id, fields in messages:
                payload = fields.get("payload")
                try:
                    if payload is not None:
                        messages = await asyncio.to_thread(_handle_message, payload)
                        broadcaster = get_broadcaster()
                        for message in messages:
                            broadcaster.publish(message)
                except Exception:  # noqa: BLE001 — 한 메시지 실패로 스트림 전체가 막히면 안 된다
                    telemetry_consumer_error_total.inc()
                    logger.exception("텔레메트리 메시지 처리 실패: message_id=%s", message_id)
                finally:
                    await client.xack(TELEMETRY_STREAM, CONSUMER_GROUP, message_id)
