# Command 모듈

책임: 명령 요청·승인·전달·ACK·취소·타임아웃 상태 머신
(`/commands`, `/commands/{id}/approve|cancel|ack|execute|result`).

`docs/planning/02_백엔드_아키텍처.md`: Command는 서버→기체 저빈도 제어 의도이며 인증·승인·
ACK·감사 추적이 필수다. Telemetry(기체→서버, 고빈도, 유실 허용)와 계약·스트림·API·서비스
계정을 항상 분리한다.

## 상태 머신 (5단계 완료)

```
DRAFT → PENDING_APPROVAL → APPROVED → DISPATCHED → ACKNOWLEDGED → EXECUTING
  → SUCCEEDED / FAILED / TIMED_OUT / CANCELLED
```

`POST /commands`는 이미 승인을 구하는 완전한 요청이라 `DRAFT`를 건너뛰고 곧바로
`PENDING_APPROVAL`로 생성한다(`state_machine.py` 참고, `DRAFT`는 향후 "임시 저장" 기능을
위해 남겨둔 자리).

- `state_machine.py` — 전이 그래프(`TRANSITIONS`), 취소 가능 상태(`CANCELLABLE_STATUSES`),
  터미널 상태(`TERMINAL_STATUSES`). 허용 안 된 전이는 `InvalidTransition`(→ 409).
- `repository.py` — `approve_and_dispatch`(요청자 본인 승인 거부, 승인 즉시 만료 확인 후
  자동 전달까지 진행 — 사람이 개입하는 별도 "전달" 단계 없음), `cancel_command`(취소
  가능 상태에서만), `acknowledge_command`/`start_executing_command`/
  `report_command_result`(기체 측 진행 보고), `force_timeout`.
- `timeout_worker.py` — `run_timeout_worker`: 5초 주기로 `expires_at`이 지났지만 아직
  종결 상태가 아닌 명령을 전부 `TIMED_OUT`으로 전이(앱 lifespan 백그라운드 task,
  telemetry consumer와 같은 패턴). `CommandEnvelope`에 마감이 `expires_at` 하나뿐이라
  단계별 별도 기한은 없고, "그 시점에 어느 단계였는지"를 이벤트 detail에 남겨 구분한다.
- 승인 시 만료 전이면 Command Redis Stream(`aeroops:command:events`)에 발행한다 —
  **승인 전에는 발행하지 않는다**("승인되지 않았거나 만료된 명령은 전달되지 않는다").
- 주요 행위(생성/승인/취소)는 `audit` 모듈로 감사 로그에 남는다.

## 채널 분리

- `streams.py` — Command 채널 전용 Redis 스트림/소비자 그룹 이름(Telemetry와 분리).
- 채널 분리(ACL)는 `app/core/redis_acl.py`가 앱 시작 시 등록한다 — `telemetry` 계정은
  `aeroops:telemetry:*` 키만, `command` 계정은 `aeroops:command:*` 키만 접근 가능.

## 알려진 제한

- Command Redis Stream을 실제로 소비해 기체에 전달하는 주체가 없다(발행만 하고 아무도
  안 읽음) — 실제 기체(mTLS)가 붙는 8단계 전까지는 `/commands/{id}/ack|execute|result`를
  운영자·시험 스크립트가 직접 호출해 기체 역할을 대신한다.
- 명령 승인자/요청자는 인증되지 않은 자유 문자열이다(8단계에서 실제 사용자 인증 연동).
