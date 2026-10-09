"""`/ws/operations` WebSocket — 최신 상태·미확인 경보 스냅샷 + 실시간 갱신 구독.

`docs/roadmap/04_단계_2D실시간관제_Day08-10.md`: 연결 시 전체 기체의 최신 상태 스냅샷을
보내고, 이후 갱신되는 기체·새 경보만 스트리밍한다. 별도 "resume" 프로토콜은 없다 —
클라이언트는 재연결만 하면 항상 새 스냅샷으로 복구된다(단순함 우선, MVP).
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket

from app.db.base import SessionLocal
from app.modules.alert.repository import list_alerts
from app.modules.alert.schemas import AlertOut
from app.modules.realtime.broadcaster import get_broadcaster
from app.modules.telemetry.repository import get_all_latest_states
from app.modules.telemetry.schemas import frame_from_record

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])


def _fetch_snapshot() -> dict:
    """동기 DB 조회. 이벤트 루프를 막지 않도록 `asyncio.to_thread`에서 호출된다."""
    with SessionLocal() as db:
        assets = [frame_from_record(r).model_dump(mode="json") for r in get_all_latest_states(db)]
        open_alerts = [
            AlertOut.model_validate(a).model_dump(mode="json")
            for a in list_alerts(db, status="OPEN")
        ]
    return {"assets": assets, "alerts": open_alerts}


@router.websocket("/ws/operations")
async def operations_ws(websocket: WebSocket) -> None:
    await websocket.accept()

    snapshot = await asyncio.to_thread(_fetch_snapshot)
    await websocket.send_json({"type": "snapshot", **snapshot})

    broadcaster = get_broadcaster()
    queue = broadcaster.subscribe()

    async def _forward_updates() -> None:
        while True:
            message = await queue.get()
            await websocket.send_json(message)

    async def _watch_for_disconnect() -> None:
        # 클라이언트가 먼저 보내는 메시지는 없지만, 연결 종료(close frame)는 여기서 감지된다.
        while True:
            await websocket.receive_text()

    forward_task = asyncio.create_task(_forward_updates())
    watch_task = asyncio.create_task(_watch_for_disconnect())
    try:
        await asyncio.wait({forward_task, watch_task}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        broadcaster.unsubscribe(queue)
        forward_task.cancel()
        watch_task.cancel()
        await asyncio.gather(forward_task, watch_task, return_exceptions=True)
