# Realtime 모듈

책임: WebSocket 연결·구독·재연결 지원 (`/ws/operations`).

## 구현 (4단계)

- `router.py` — 연결 시 전체 기체 최신 상태 스냅샷을 한 번 보내고, 이후 `broadcaster`가
  전달하는 갱신만 스트리밍한다. 별도 "resume" 프로토콜은 없다 — 클라이언트는 재연결만
  하면 항상 새 스냅샷을 받는다(단순함 우선, MVP).
- `broadcaster.py` — 프로세스 내(`asyncio.Queue` 기반) 브로드캐스터.
  `telemetry.consumer`가 `asset_latest_state`를 갱신할 때마다(중복·역순이 아닐 때만)
  발행한다. ADR 0001(단일 프로세스 모놀리스)이라 Redis Pub/Sub 대신 in-process로
  충분하다 — API를 여러 인스턴스로 늘리면 Redis Pub/Sub으로 옮겨야 한다.

경보(`alert`) 구독은 5단계에서 이 라우터에 추가한다.
