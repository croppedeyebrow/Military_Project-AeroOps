# ADR 0005: Telemetry `boot_id` 도입과 멱등 키 변경

- 상태: **승인됨** (2026-10-24, 사용자 승인. DDL은 ADR 0004 결정에 따라 Alembic이 아니라 Flyway로 수행)
- 일자: 2026-10-24
- 관련: [ADR 0004](0004-strangler-transition-to-kotlin-c2-core.md), `docs/planning/06_시스템_디자인_상세.md`(멱등 키 `(asset_id, boot_id, sequence_no)`)

## 배경: 현재 코드의 실제 결함

현행 FastAPI는 `(asset_id, sequence_no)` 유일 제약으로 중복을 판정한다
(`backend/app/modules/telemetry/models.py` `uq_telemetry_asset_sequence`,
`repository.insert_raw_frame`). 기체(시뮬레이터 포함)가 재부팅·재시작하면 `sequence_no`가
0부터 다시 시작하므로 다음 문제가 생긴다.

1. **새 부팅의 프레임이 전부 "중복"으로 폐기된다.** 7단계 부하 시험에서 같은 seed로 시뮬레이터를
   다시 돌렸을 때 `telemetry_duplicate_total`이 전체 건수만큼 올라간 것이 이 현상이다.
2. **재동기화가 재부팅을 구분하지 못한다.** `sync/repository._compute_sequence_gap`은 서버
   최대 sequence가 기체 보고값보다 크면 `device_behind_server`로 분류한다. 정상 재부팅도 이
   이상 징후로 보인다.
3. 최신 상태 후퇴 방지는 `event_time`만으로 판정(`upsert_latest_state_if_newer`)해서 sequence
   리셋 자체는 영향이 없지만, 위 1·2번 때문에 "새 부팅의 데이터가 저장되지 않는" 문제가 먼저 생긴다.

## 결정

### 의미

- `boot_id`는 **기체(또는 Edge Agent/시뮬레이터)가 전원 투입·프로세스 시작마다 새로 만드는
  불투명 식별자**다. 한 부팅 동안 바뀌지 않는다.
- `sequence_no`는 **같은 `boot_id` 안에서만** 0부터 단조 증가한다. 부팅이 바뀌면 다시 0이다.
- 형식: 1~64자, `[A-Za-z0-9_-]`. 실제 기체는 UUIDv4 권장. **부팅 간 순서를 의미하지 않는다**
  (정렬 키로 쓰지 않는다).
- 부팅 간 순서는 `event_time`과 서버 최초 수신 시각(`received_at`)으로 판단한다.

### 멱등 키·불변조건

- 중복 판정 키: `(asset_id, boot_id, sequence_no)`.
- 최신 상태 후퇴 방지는 현행대로 `event_time` 기준을 유지하고, 동일 `event_time`이면 같은
  `boot_id` 안에서 더 큰 `sequence_no`만 갱신한다.
- 재동기화는 **같은 `boot_id`** 의 서버 최대 sequence와만 비교한다. 서버가 모르는 `boot_id`는
  `anomaly="new_boot"`(정보성)로 기록하고 손실 구간은 `0..reported_last_sequence_no` 전체를
  미수신으로 본다. `device_behind_server`는 같은 `boot_id` 안에서 서버가 더 앞설 때만 쓴다.

### 하위 호환(Expand → Migrate → Contract)

- `schema_version=1` 프레임(`boot_id` 없음)은 서버가 `boot_id="legacy"`로 정규화한다 — 현행
  동작과 동일(`(asset_id, "legacy", sequence_no)`)하므로 Golden Replay가 그대로 유효하다.
- `schema_version=2`부터 `boot_id` 필수. FastAPI와 Kotlin이 공존하는 동안 둘 다 v1/v2를 받는다.
- 모든 생산자(Rust Gateway·C++ 시뮬레이터)가 v2로 전환된 뒤 `legacy` 수용을 제거(Contract 단계)한다.

## 변경 범위 (이 ADR은 문서만 — 구현은 별도 유닛)

| 영역 | 변경 |
|---|---|
| Wire 계약 | `TelemetryFrame`에 `boot_id: str \| None`(v1) → 필수(v2). OpenAPI·WS·Redis payload 기준선(`tests/contracts/baseline`) 재생성 필요 |
| DB (Flyway, 두 단계로 분리) | **Expand(먼저)**: `telemetry_frames`, `asset_latest_state`, `sync_sessions`에 `boot_id text not null default 'legacy'` 추가 — legacy 코드가 깨지지 않는다. **Contract(Operational Picture 쓰기 이전 시점)**: 유일 제약을 `(asset_id, sequence_no)` → `(asset_id, boot_id, sequence_no)`로 교체. 기존 행은 `legacy`로 자동 채워짐 |
| Backend | `insert_raw_frame`/`get_max_sequence_no`를 `boot_id` 범위로 조회, `SyncRequest`에 `boot_id` 추가, `_compute_sequence_gap`에 `new_boot` 처리. `event_log.stream_sequence`(텔레메트리 채널은 `sequence_no`)는 부팅 간 단조가 아니므로 정렬은 `event_time, id`에 의존함을 확인·문서화(현행 정렬 키는 `event_time, stream_sequence, id`) |
| Simulator | 실행(부팅)마다 `boot_id` 생성(재현성을 위해 seed·asset·부팅 순번에서 UUIDv5로 결정적 생성). 새 장애 유형 `reboot`(중간에 `boot_id` 교체 + sequence 0 재시작) 추가 |
| Frontend | 영향 없음(WS 메시지 필드 추가만, 선택 필드) |
| 시험 | Golden Replay에 `reboot` 시나리오와 재동기화 시나리오 추가. `legacy` 경로는 기존 기준선이 회귀 시험 역할 |
| 문서 | `planning/03`(유일 제약)·`planning/05`(필드 목록) 갱신, 구현 시 `docs/api/telemetry_frame_dictionary.md` 갱신 |

## 적용 시점 제약 (ADR 0004 결정에서 파생)

유일 제약 교체를 Expand와 같이 하면 안 된다. legacy는 `insert_raw_frame`에서
`ON CONFLICT (asset_id, sequence_no)`를 쓰므로 옛 제약을 지우면 깨진다. 반대로 옛 제약이 남아 있으면
Kotlin이 새 부팅의 `sequence_no=0`을 쓰는 순간 이전 부팅의 같은 번호와 충돌한다. 그래서 **제약 교체는
Telemetry 쓰기 주체가 legacy에서 Kotlin으로 넘어가는 시점**(`new_roadmap` 3단계 승격)에 함께 수행한다.
그 전까지 legacy는 부팅 리셋 결함을 그대로 가진 채 동작한다(알려진 제한).

## 범위 밖 / 후속

- 기체 재부팅 후 "이미 실행한 command_id 기억"은 기체 측 영속화 문제라 이 ADR의 범위가 아니다
  (`docs/planning/11` 불변조건 2, 재동기화의 `last_processed_command_id`로 조정).
- 시간 동기화·Clock Skew로 인한 부팅 간 `event_time` 역전은 별도 품질 모델(Operational
  Picture, new_roadmap 3단계)에서 다룬다.

## 대안과 기각 이유

- **서버가 부팅을 추정**(sequence가 작아지면 새 부팅으로 간주): 역순·지연 프레임과 구분할 수 없다.
- **`sequence_no`를 부팅 간 단조로 유지**(영속 저장): 기체 저장소 장애 시 즉시 깨지고, 시뮬레이터·
  Edge에 영속 상태를 강제한다.
- **부팅 카운터 정수(`boot_seq`)**: 순서를 주지만 영속 저장이 필요해 위와 같은 문제를 가진다.
