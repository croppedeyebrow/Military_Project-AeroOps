"""프로세스 내 실시간 브로드캐스터 — 연결된 `/ws/operations` 클라이언트들에게 최신 상태
갱신·경보를 전달한다.

ADR 0001(단일 프로세스 모놀리스)이라 telemetry consumer와 WebSocket 핸들러가 같은
프로세스 안에 있다. 그래서 Redis Pub/Sub 대신 `asyncio.Queue` 기반의 단순한 in-process
broadcast로 충분하다 — 나중에 API를 여러 인스턴스로 늘리면 Redis Pub/Sub으로 옮겨야 한다
(그때는 Telemetry/Command처럼 별도 채널·ACL을 또 고민해야 한다는 뜻이기도 하다).

느린 구독자(웹소켓 클라이언트) 하나 때문에 consumer가 막히면 안 되므로, 큐가 가득 차면
가장 오래된 항목을 버리고 계속 진행한다("최신 상태"만 의미 있고, 밀린 이력을 다 보내는
게 목적이 아니기 때문).

메시지는 이미 `{"type": "update", "asset": {...}}` / `{"type": "alert", "alert": {...}}`
형태로 완성된 dict를 받는다 — 브로드캐스터 자체는 내용을 모르고 그대로 전달만 한다
(`realtime/router.py`가 그대로 `send_json`한다).
"""
from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from app.core.metrics import realtime_broadcast_messages_total, realtime_ws_connections

_QUEUE_MAXSIZE = 100

OperationsMessage = dict[str, Any]


class OperationsBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._subscribers.add(queue)
        realtime_ws_connections.inc()
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)
        realtime_ws_connections.dec()

    def publish(self, message: OperationsMessage) -> None:
        """구독자 전원에게 메시지를 전달한다. 큐가 가득 찬 구독자는 가장 오래된 항목을 버린다."""
        # 구독자 수와 무관하게 "발행 횟수" 자체를 센다 — 구독자가 0명이어도(아무도 안
        # 보고 있어도) consumer가 경보/갱신을 얼마나 자주 만들어내는지는 알 수 있어야
        # 한다("WS 연결 수"와 "발행량"은 서로 다른 질문).
        realtime_broadcast_messages_total.labels(message_type=message.get("type", "unknown")).inc()
        for queue in self._subscribers:
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(message)


_broadcaster = OperationsBroadcaster()


def get_broadcaster() -> OperationsBroadcaster:
    return _broadcaster
