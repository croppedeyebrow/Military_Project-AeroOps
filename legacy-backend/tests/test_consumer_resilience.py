"""처리 실패한 텔레메트리가 유실되지 않는다 — consumer 재전달·dead-letter 시험(D-2).

이전에는 consumer가 처리에 실패해도 항상 XACK해서, DB가 순간 끊긴 때의 프레임이 202를 받고도
영구 유실됐다. 실제 Postgres/Redis가 필요하다(없으면 스킵). consumer는 `live_client`가 띄운
앱 안에서 이미 돌고 있으므로, 모듈 상수를 줄여 재전달이 빨리 일어나게 한다.
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.redis import get_telemetry_redis
from app.modules.telemetry import consumer

WAIT_S = 20.0


def _frame(asset_id: str) -> dict:
    return {
        "asset_id": asset_id,
        "event_time": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        "sequence_no": 0,
        "latitude": 37.4,
        "longitude": 127.1,
        "altitude_m": 50.0,
        "battery_pct": 90.0,
    }


async def _wait_for_dead_letter(client, original_id: str) -> dict:
    deadline = time.monotonic() + WAIT_S
    while time.monotonic() < deadline:
        for _entry_id, fields in await client.xrange(consumer.DEAD_LETTER_STREAM, "-", "+"):
            if fields.get("original_id") == original_id:
                return fields
        await asyncio.sleep(0.2)
    raise AssertionError(f"dead-letter에 {original_id}가 나타나지 않았다")


async def _is_pending(client, message_id: str) -> bool:
    pending = await client.xpending_range(
        consumer.TELEMETRY_STREAM, consumer.CONSUMER_GROUP, min=message_id, max=message_id, count=1
    )
    return bool(pending)


def _fast_redelivery(monkeypatch) -> None:
    monkeypatch.setattr(consumer, "RECLAIM_MIN_IDLE_MS", 200)
    monkeypatch.setattr(consumer, "RECLAIM_INTERVAL_S", 0.2)
    monkeypatch.setattr(consumer, "BLOCK_MS", 300)


@pytest.mark.asyncio
async def test_unparseable_payload_goes_to_dead_letter_and_is_acked(live_client: TestClient):
    client = get_telemetry_redis()
    message_id = await client.xadd(consumer.TELEMETRY_STREAM, {"payload": "not-json"})

    entry = await _wait_for_dead_letter(client, message_id)

    assert entry["reason"] == "invalid_payload"
    assert entry["payload"] == "not-json"
    assert not await _is_pending(client, message_id)


@pytest.mark.asyncio
async def test_message_without_payload_goes_to_dead_letter(live_client: TestClient):
    client = get_telemetry_redis()
    message_id = await client.xadd(consumer.TELEMETRY_STREAM, {"unexpected": "field"})

    entry = await _wait_for_dead_letter(client, message_id)

    assert entry["reason"] == "missing_payload"
    assert not await _is_pending(client, message_id)


@pytest.mark.asyncio
async def test_transient_failure_is_redelivered_and_frame_is_saved(
    live_client: TestClient, monkeypatch
):
    """DB 순단으로 첫 처리가 실패해도 ACK되지 않고 재전달되어 결국 저장된다."""
    _fast_redelivery(monkeypatch)
    asset_id = f"transient-{uuid.uuid4().hex[:8]}"
    original = consumer._handle_message
    calls = {"n": 0}

    def flaky(payload: str):
        if asset_id in payload:
            calls["n"] += 1
            if calls["n"] == 1:
                raise OperationalError("INSERT", {}, Exception("connection lost"))
        return original(payload)

    monkeypatch.setattr(consumer, "_handle_message", flaky)

    assert live_client.post("/telemetry", json=_frame(asset_id)).status_code == 202

    deadline = time.monotonic() + WAIT_S
    status = None
    while time.monotonic() < deadline:
        status = live_client.get(f"/assets/{asset_id}/latest").status_code
        if status == 200:
            break
        await asyncio.sleep(0.2)

    assert status == 200, "재전달되지 않아 프레임이 유실됐다"
    assert calls["n"] >= 2


@pytest.mark.asyncio
async def test_exhausted_retries_move_to_dead_letter(live_client: TestClient, monkeypatch):
    """계속 실패하면 MAX_DELIVERIES 이후 무한 재시도하지 않고 dead-letter로 이동한다."""
    _fast_redelivery(monkeypatch)
    monkeypatch.setattr(consumer, "MAX_DELIVERIES", 2)
    asset_id = f"doomed-{uuid.uuid4().hex[:8]}"
    original = consumer._handle_message

    def always_fails(payload: str):
        if asset_id in payload:
            raise OperationalError("INSERT", {}, Exception("db is down"))
        return original(payload)

    monkeypatch.setattr(consumer, "_handle_message", always_fails)

    client = get_telemetry_redis()
    message_id = await client.xadd(
        consumer.TELEMETRY_STREAM, {"payload": json.dumps(_frame(asset_id))}
    )

    entry = await _wait_for_dead_letter(client, message_id)

    assert entry["reason"] == "max_deliveries"
    assert asset_id in entry["payload"]
    assert not await _is_pending(client, message_id)
    assert live_client.get(f"/assets/{asset_id}/latest").status_code == 404
