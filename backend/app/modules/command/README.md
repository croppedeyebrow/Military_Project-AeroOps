# Command 모듈

책임: 명령 요청·승인·전달·ACK·취소·타임아웃 상태 머신 (`/commands`, `/commands/{id}/ack`).

`docs/planning/02_백엔드_아키텍처.md`: Command는 서버→기체 저빈도 제어 의도이며 인증·승인·
ACK·감사 추적이 필수다. Telemetry(기체→서버, 고빈도, 유실 허용)와 계약·스트림·API·서비스
계정을 항상 분리한다.

## 상태 머신

```
DRAFT → PENDING_APPROVAL → APPROVED → DISPATCHED → ACKNOWLEDGED → EXECUTING
  → SUCCEEDED / FAILED / TIMED_OUT / CANCELLED
```

- 요청자와 승인자를 분리한다.
- `command_id`와 `idempotency_key`로 중복 실행을 막는다.
- 취소는 별도 명령 이벤트이며 이미 완료된 작업을 되돌렸다고 간주하지 않는다.
- timeout은 전달 실패, ACK 지연, 실행 초과를 구분한다.

## 구현 (3단계 보정 완료 — 최소 골격)

- `router.py` — `POST /commands`: idempotency key 기반 멱등 생성. 같은 키+같은 내용 재요청은
  기존 명령을 그대로 반환(200), 같은 키+다른 내용은 409. 성공 시 Command Redis Stream
  (`aeroops:command:events`)에도 발행한다(best-effort — DB 커밋이 먼저이므로 발행 실패가
  명령 생성 자체를 실패시키지 않는다).
- `repository.py` — `create_command_idempotent`: `commands` insert + `command_events`에
  `CREATED` 이벤트 기록을 한 트랜잭션으로 처리. `payload_hash`(SHA-256)로 내용 동일성을
  판단한다(원본 payload는 `command_events.detail`에 보존).
- `models.py` — `Command`(현재 상태 스냅샷), `CommandEvent`(append-only 이력).
- `streams.py` — Command 채널 전용 Redis 스트림/소비자 그룹 이름(Telemetry와 분리).
- 채널 분리(ACL)는 `app/core/redis_acl.py`가 앱 시작 시 등록한다 — `telemetry` 계정은
  `aeroops:telemetry:*` 키만, `command` 계정은 `aeroops:command:*` 키만 접근 가능.

상태 전이(승인/전달/ACK/실행/취소/timeout worker)는 아직 없다 — **status는 항상 `DRAFT`**로
남는다. 5단계에서 완성한다.

## 로드맵

- 5단계(`docs/roadmap/05_단계_임무경보관리_Day11-13.md`): 상태 머신 완성, 승인/전달/ACK/취소,
  timeout worker, `GET /commands`, `POST /commands/{id}/approve|cancel|ack`.

## 예정 구성 (5단계 이후)

- `state_machine.py` — 전이 검증
- `timeout_worker.py` — 단계별 기한 판정 백그라운드 task
