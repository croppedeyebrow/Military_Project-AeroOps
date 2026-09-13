# AeroOps Backend

FastAPI 기반 모듈형 모놀리스. `docs/planning/02_백엔드_아키텍처.md` 참고.

## 로컬 실행

3단계부터는 실제 PostgreSQL/PostGIS·Redis가 필요하다(수집 API가 Redis Stream에 발행하고,
백그라운드 consumer가 DB에 반영한다). 가장 간단한 방법은 인프라 서비스만 Docker로 띄우고
API는 로컬에서 직접 실행하는 것이다.

```bash
# 저장소 루트에서: postgres/redis만 띄운다
docker compose -f infra/docker-compose.yml up -d postgres redis

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

- API 문서: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health/ready (DB·Redis 연결 상태를 함께 보여준다)
- 메트릭: http://localhost:8000/metrics

## 테스트 / 린트

```bash
ruff check .
pytest              # postgres/redis가 없으면 통합 테스트(tests/test_ingestion_pipeline.py)는 스킵된다
mypy app
```

## 모듈 구조

`app/modules/{ingestion,telemetry,mission,alert,realtime,identity,audit,command,
device_identity,sync,deployment}` — 각 모듈 README에 책임과 로드맵 단계를 정리했다.
구현 완료: `ingestion`(수집 API), `telemetry`(consumer, 조회 API), `command`(idempotency
key 기반 최소 골격), `deployment`(build-info), `realtime`(`/ws/operations`),
`sync`(재동기화 handshake). 자세한 내용은
[`docs/dev_history/03_단계_수집저장파이프라인.md`](../docs/dev_history/03_단계_수집저장파이프라인.md),
[`docs/dev_history/04_단계_2D실시간관제.md`](../docs/dev_history/04_단계_2D실시간관제.md).

## 처리 흐름 — Telemetry/Command 채널 분리

`POST /telemetry`는 계약 검증(422 거부 가능) 후 Telemetry Redis Stream에 발행만 하고 즉시
202를 반환한다. 실제 DB 저장·최신 상태 갱신은 앱 수명 동안 떠 있는 백그라운드 consumer
(`app/modules/telemetry/consumer.py`)가 비동기로 처리한다 — 요청 경로를 느린 작업으로
막지 않기 위해서다(`docs/planning/02_백엔드_아키텍처.md`).

`POST /commands`는 반대로 **DB 트랜잭션이 먼저**다(idempotency key 유일성, `commands`+
`command_events` 커밋) — Command는 저빈도·강한 일관성이 필요해서다. 커밋 후 Command Redis
Stream에도 best-effort로 발행한다.

두 채널은 물리적으로 분리되어 있다: 서로 다른 Redis Stream(`aeroops:telemetry:raw` vs
`aeroops:command:events`)과, 앱이 시작할 때 스스로 등록하는 서로 다른 Redis ACL 계정
(`app/core/redis_acl.py`) — `telemetry` 계정은 telemetry 스트림만, `command` 계정은
command 스트림만 접근할 수 있다. 한쪽 계정으로 다른 채널에 쓰려 하면 Redis가
`NoPermissionError`로 거부한다(`tests/test_redis_acl.py`).

## 실시간 관제·재동기화 (4단계)

- `GET /assets` — 전체 기체 최신 상태 목록(프론트 초기 페인트용).
- `WS /ws/operations` — 연결 시 전체 스냅샷 1회, 이후 갱신되는 기체만 스트리밍. 재연결
  시 서버가 새 스냅샷을 다시 보내므로 클라이언트는 그냥 재연결만 하면 된다.
- `POST /devices/{asset_id}/sync` — 기체가 마지막 `sequence_no`/`state_version`/
  `last_processed_command_id`를 보고하면, 서버가 손실 구간(sequence gap)·미종결 명령·
  snapshot 재발급 여부를 판단해 응답하고 `sync_sessions`에 기록한다.
