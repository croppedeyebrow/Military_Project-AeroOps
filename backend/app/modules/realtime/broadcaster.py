"""프로세스 내 실시간 브로드캐스터 — 연결된 `/ws/operations` 클라이언트들에게 최신 상태
갱신을 전달한다.

ADR 0001(단일 프로세스 모놀리스)이라 telemetry consumer와 WebSocket 핸들러가 같은
프로세스 안에 있다. 그래서 Redis Pub/Sub 대신 `asyncio.Queue` 기반의 단순한 in-process
broadcast로 충분하다 — 나중에 API를 여러 인스턴스로 늘리면 Redis Pub/Sub으로 옮겨야 한다
(그때는 Telemetry/Command처럼 별도 채널·ACL을 또 고민해야 한다는 뜻이기도 하다).

느린 구독자(웹소켓 클라이언트) 하나 때문에 consumer가 막히면 안 되므로, 큐가 가득 차면
가장 오래된 항목을 버리고 계속 진행한다("최신 상태"만 의미 있고, 밀린 이력을 다 보내는
게 목적이 아니기 때문).
"""
from __future__ import annotations

import asyncio
import contextlib

from app.schemas.telemetry import TelemetryFrame

_QUEUE_MAXSIZE = 100


class AssetUpdateBroadcaster:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def publish(self, frame: TelemetryFrame) -> None:
        """구독자 전원에게 갱신을 알린다. 큐가 가득 찬 구독자는 가장 오래된 항목을 버린다."""
        for queue in self._subscribers:
            if queue.full():
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(frame)


_broadcaster = AssetUpdateBroadcaster()


def get_broadcaster() -> AssetUpdateBroadcaster:
    return _broadcaster
