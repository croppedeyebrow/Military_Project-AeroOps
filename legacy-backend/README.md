# AeroOps Backend (legacy — FastAPI)

> **전환 중(ADR 0004)**: 이 FastAPI 구현은 Kotlin C2 Core(`../backend/`)가 대체해 가는 기준 구현이다.
> 삭제하지 않고 Golden Replay·계약 기준선의 비교 대상이자 전환 기간 운영 구현으로 유지한다.
>
> **스키마 소유는 이제 Kotlin(Flyway)이다. Alembic은 `0005`에서 동결됐다.**
> - 이 모듈에 새 Alembic 마이그레이션(`0006` 이상)을 추가하지 않는다. DB 변경은 `../backend/`의
>   `bootstrap/src/main/resources/db/migration/`에 Flyway 파일(V2 이상)로 한다.
> - Flyway 변경은 이 모듈이 깨지지 않는 **Expand 전용**(컬럼 추가·새 테이블)이어야 한다(ADR 0004 "영향").
> - `alembic upgrade head`는 계속 동작한다(0005까지). 빈 DB를 만들 때는 둘 중 하나를 쓰면 같은 스키마가
>   된다 — 두 경로의 동등성은 Kotlin 쪽 `SchemaEquivalenceTest`가 매번 검증한다.

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
구현 완료: `ingestion`(수집 API), `telemetry`(consumer, 조회 API), `command`(승인·전달·
ACK·실행·결과·취소·타임아웃 상태 머신), `mission`(임무·경로·구역), `alert`(경보 규칙),
`audit`(감사 로그), `deployment`(build-info), `realtime`(`/ws/operations`),
`sync`(재동기화 handshake). 자세한 내용은
[`docs/dev_history/`](../docs/dev_history/legacy/)의 단계별 문서.

## 처리 흐름 — Telemetry/Command 채널 분리

`POST /telemetry`는 계약 검증(422 거부 가능) 후 Telemetry Redis Stream에 발행만 하고 즉시
202를 반환한다. 실제 DB 저장·최신 상태 갱신은 앱 수명 동안 떠 있는 백그라운드 consumer
(`app/modules/telemetry/consumer.py`)가 비동기로 처리한다 — 요청 경로를 느린 작업으로
막지 않기 위해서다(`docs/planning/02_백엔드_아키텍처.md`). 최신 상태가 실제로 갱신되면
같은 consumer가 경보 규칙(`alert` 모듈)도 평가한다.

`POST /commands`는 반대로 **DB 트랜잭션이 먼저**다(idempotency key 유일성, `commands`+
`command_events` 커밋) — Command는 저빈도·강한 일관성이 필요해서다. Redis Stream 발행은
**승인 시점**(그것도 자동 전달까지 성공했을 때만)으로 미뤄둔다 — 승인되지 않은 명령이
기체가 볼 수 있는 채널에 아예 나타나지 않게 하기 위해서다.

두 채널은 물리적으로 분리되어 있다: 서로 다른 Redis Stream(`aeroops:telemetry:raw` vs
`aeroops:command:events`)과, 앱이 시작할 때 스스로 등록하는 서로 다른 Redis ACL 계정
(`app/core/redis_acl.py`) — `telemetry` 계정은 telemetry 스트림만, `command` 계정은
command 스트림만 접근할 수 있다. 한쪽 계정으로 다른 채널에 쓰려 하면 Redis가
`NoPermissionError`로 거부한다(`tests/test_redis_acl.py`).

## 실시간 관제·재동기화 (4단계)

- `GET /assets` — 전체 기체 최신 상태 목록(프론트 초기 페인트용).
- `WS /ws/operations` — 연결 시 전체 기체 스냅샷 + 미확인 경보 스냅샷을 1회 보내고,
  이후 갱신되는 기체·새 경보만 스트리밍. 재연결 시 서버가 새 스냅샷을 다시 보내므로
  클라이언트는 그냥 재연결만 하면 된다.
- `POST /devices/{asset_id}/sync` — 기체가 마지막 `sequence_no`/`state_version`/
  `last_processed_command_id`를 보고하면, 서버가 손실 구간(sequence gap)·미종결 명령·
  snapshot 재발급 여부를 판단해 응답하고 `sync_sessions`에 기록한다.

## 임무·경보·명령 수명주기 (5단계)

- `POST/GET/PATCH /missions`, `PUT/GET /missions/{id}/route`, `POST/GET /geofences`.
- `GET /alerts`, `POST /alerts/{id}/acknowledge|resolve` — 경보 생성은 telemetry
  consumer가 규칙 평가로 자동 발생시킨다(`app/modules/alert/rules.py`).
- `POST /commands/{id}/approve|cancel|ack|execute|result`, `GET /commands`,
  `GET /commands/{id}`(이벤트 이력 포함) — 상세는 `app/modules/command/README.md`.
- `GET /audit-logs` — 임무·구역·명령·경보 변경 행위 조회.
