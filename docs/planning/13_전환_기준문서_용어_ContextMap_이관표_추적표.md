# 전환 기준 문서 — 용어 사전·Context Map·이관표·불변조건·추적표

`docs/new_roadmap/01_기준선과_전환계약_Day01.md`의 산출물이다. 기준일: 2026-10-24, 대상은 현행
FastAPI 구현(7단계 완료)이며, 모든 "현행" 서술은 코드·시험에서 확인한 사실이다. 목표 구조는
`10_방산_DDD_언어별_책임_아키텍처.md`, 전환 순서는 `12_점진적_전환_아키텍처.md`를 따른다.

## 1. Ubiquitous Language 사전

| 용어 | 정의 | 쓰지 않는 말 | 현행 구현 |
|---|---|---|---|
| 기체(Asset) | 관제 대상 무인체계 1대. `asset_id`로 식별 | 드론 ID, device(통신 장비 의미일 때만 사용) | `assets` |
| 부팅(Boot)·`boot_id` | 기체가 전원 투입·프로세스 시작마다 만드는 식별자. `sequence_no`의 범위 | 세션(운용 세션과 혼동) | 없음(ADR 0005) |
| 관측(Observation) | 외부 Wire 프레임을 도메인 규칙으로 변환한 "기체가 보고한 사실" | 데이터 포인트 | `TelemetryFrame`(Wire 모델과 미분리) |
| 최신 상황(Latest State) | 기체별 가장 최근 관측으로 만든 재생성 가능한 Projection | 현재 상태(사실처럼 들림) | `asset_latest_state` |
| 연결 신선도(Freshness) | 마지막 수신 후 경과 시간 기준 LIVE/STALE/DISCONNECTED | 온라인/오프라인 | 프론트 `classifyFreshness` |
| 데이터 품질(Quality) | 관측 값 자체의 신뢰도 KNOWN/STALE/PARTIAL/INVALID/UNKNOWN. 신선도와 별개 | — | 없음(Kotlin 3단계) |
| 명령(Command) | 운용자가 기체에 내리는 제어 의도. `command_id`·`idempotency_key`로 식별 | 주문, 작업, 지시 | `commands` |
| 승인(Approval) | 요청자와 다른 권한자가 명령을 허가하는 행위 | 확인(경보 확인과 혼동) | 본인 승인 금지만 구현 |
| 전달(Dispatch) | 승인된 명령을 Command Stream에 발행 | 전송(Telemetry 방향과 혼동) | 승인 시 자동 |
| ACK | 기체가 명령을 **수신**했다는 응답. 실행·완료가 아니다 | 완료, 성공 | `ACKNOWLEDGED` |
| 실행 결과 | 기체가 보고한 SUCCEEDED/FAILED. 목표 상태 도달 검증과 별개 | — | `/commands/{id}/result` |
| 효과 검증(Effect Verification) | 명령 후 관측으로 목표 상태 도달을 확인 | — | 없음(Kotlin 4단계) |
| UNKNOWN | ACK·결과가 없어 기체의 처리 여부를 모르는 상태. 실패가 아니다 | 실패, 타임아웃(처리 여부 단정 시) | 현행은 `TIMED_OUT`(§4 불변조건 3) |
| 통제권(ControlLease) | 기체를 특정 운용자·세션이 통제하는 기간 한정 권한 | 소유권 | 없음(Kotlin 4단계) |
| 운용 세션(OperationSession) | 하나의 배포 버전에 고정된 운용 구간 | 로그인 세션 | `operation_sessions` |
| 배포(Deployment) | Git SHA·이미지 digest·schema/rule/config 버전의 묶음 | 릴리스 | `deployments` |
| 경보(Alert) | 규칙 1개가 만든 개별 이상 징후 | 알림 | `alerts` |
| 사건(Incident) | 관련 경보를 묶어 조치를 추적하는 단위 | 이슈 | 없음(Kotlin 단계 미정) |
| 지오펜스(Geofence) | 허용·금지 공간 구역 | 구역(임무 구역과 혼동) | `geofences` |
| 재동기화(Sync) | 재연결 후 sequence·상태·미종결 명령을 대조하는 절차 | 복구, 재접속(전송 계층만 의미) | `sync_sessions` |
| 재생(Replay) | 기록된 Event를 event-time 순서로 되돌려 보는 것 | 시뮬레이션 | `/operation-sessions/{id}/replay` |
| Golden Replay | 현행 구현의 결과를 정답으로 고정한 기준선 | — | `tests/contracts/golden` |
| System of Record | 한 Context의 쓰기를 소유하는 단 하나의 구현 | 마스터 | ADR 0004 |

## 2. Context Map

목표 경계 컨텍스트와 테이블 소유(`planning/03`의 소유권 표 기준, 현행 테이블에 대입).

| 컨텍스트 | 현행 Python 모듈 | 소유 테이블(현행) | 현행 REST 경로 |
|---|---|---|---|
| Mission Operations | `mission` | `missions`, `mission_routes` | `/missions`, `/missions/{id}`, `/missions/{id}/route` |
| Command & Control | `command` | `commands`, `command_events` | `/commands`, `/commands/{id}`, `/approve`, `/cancel`, `/ack`, `/execute`, `/result` |
| Operational Picture | `telemetry`, `ingestion`, `realtime` | `assets`, `telemetry_frames`, `asset_latest_state` | `/telemetry`, `/assets`, `/assets/{id}/latest`, `/assets/{id}/telemetry`, WS `/ws/operations` |
| Communications Resilience | `sync` | `sync_sessions` | `/devices/{asset_id}/sync` |
| Safety & Policy | `mission`(지오펜스) | `geofences` | `/geofences` |
| Incident Management | `alert` | `alerts` | `/alerts`, `/alerts/{id}/acknowledge`, `/resolve` |
| Identity & Audit | `audit`, `identity`, `device_identity` | `audit_logs` (users·roles 테이블은 아직 없음) | `/audit-logs` |
| Deployment Registry | `deployment` | `deployments`, `operation_sessions`, `event_log` | `/deployments*`, `/operation-sessions*`, `/event-log`, `/system/build-info` |
| (플랫폼) | — | — | `/health/live`, `/health/ready` |

**알려진 경계 위반 1건 — `event_log`**: Deployment Registry 소유로 두었지만, 현재 ingestion·command·
alert·sync 4개 모듈이 직접 INSERT한다(`append_event_log`). Kotlin에서는 Deployment Registry의 공개
Port(`EventLogPort.append`)나 Outbox 구독으로 바꿔야 "교차 쓰기 금지"를 지킬 수 있다. 결정은 Kotlin
4단계(Outbox) 전에 ADR로 남긴다.

의존 관계는 `10_방산_DDD_언어별_책임_아키텍처.md` §4의 표를 따른다(상류→하류: Mission Operations→
Command & Control, Communications Resilience→Operational Picture(ACL), Operational Picture→Mission
Readiness, Safety & Policy→Command & Control, Incident Management→AI Analysis, Deployment Registry→전체).

## 3. FastAPI → Kotlin 이관표

| 순서 | 대상 | 쓰기 주체 전환 | 비교 기준 | new_roadmap |
|---|---|---|---|---|
| 1 | Operational Picture(상황도 Projection) | Shadow → 승격 | Golden Replay `telemetry.*` 11종, `/assets*`·WS 계약 | 3단계 |
| 2 | Mission Operations, Safety & Policy | Kotlin이 원장 | `/missions*`, `/geofences` OpenAPI 기준선 | 4단계 |
| 3 | Command & Control | Kotlin이 원장 | Golden Replay `commands.*` 7종, `/commands*` 기준선 | 4단계 |
| 4 | Incident Management | Kotlin | Golden `alerts`(battery_low), `/alerts*` | 3~4단계 사이(미정 → 결정 필요) |
| 5 | Communications Resilience(sync) | Kotlin + Rust | `/devices/{id}/sync` 기준선, **Golden 시나리오 추가 필요** | 5단계 |
| 6 | Identity & Audit, Deployment Registry | Kotlin | `/audit-logs`, `/deployments*`, `/operation-sessions*` | 2단계(골격)·4단계 |
| 7 | Telemetry 수신 경계 | Rust Gateway가 앞단 | `/telemetry`·Redis payload 기준선 | 5단계 |

원칙(ADR 0004): 한 Context의 쓰기 주체는 하나, Dual Write 금지, FastAPI 삭제는 Replay 2회 이상과 장애
회귀 통과 후.

## 4. 제거 금지 불변조건과 현행 보장 수준

`11_현행레포_분석과_전환범위.md` §4의 8개를 현행 코드·시험에 대조했다. **"보존"과 "아직 구현 안 됨"을
구분한다.**

| # | 불변조건 | 현행 보장 | 현행 시험 | 판정 |
|---|---|---|---|---|
| 1 | 오래된 Telemetry가 최신 상태를 후퇴시키지 않는다 | `event_time` 비교 upsert | `test_ingestion_pipeline::test_out_of_order_frame_does_not_regress_latest_state`, Golden `out_of_order`·`reorder5`·`delay` | 보존 |
| 2 | 동일 `command_id`는 기체에서 두 번 실행되지 않는다 | 서버: `idempotency_key` 유일 + 재요청 시 기존 명령 반환. 기체: 시뮬레이터가 활성 명령 1개만 처리 | `test_command_api::test_same_idempotency_key_returns_existing_command_once`, Golden `idempotent`, 시뮬레이터 `command_handler` 유닛 시험 | 서버 보존 / 기체측 재부팅 후 기억은 범위 밖(ADR 0005) |
| 3 | ACK 누락을 실행 실패로 단정하지 않는다 | **현행은 `TIMED_OUT`으로 종결**(처리 여부를 구분하지 않음) | Golden `ack_lost`(TIMED_OUT) | **진화 필요**: 목표는 `UNKNOWN` 유지 + 재동기화로 조정. 결정 전까지 Golden은 현행 동작을 고정 |
| 4 | 승인과 Dispatch 사이에 권한·통제권·만료를 재검사한다 | **만료만** 승인 전·후 2회 확인, 본인 승인 금지. 권한·통제권·세션·정책·신선도 재검사는 없음 | `test_command_lifecycle::test_approve_already_expired_command_times_out_instead_of_dispatching`, `test_self_approval_rejected` | **부분 구현**(만료만). 나머지는 Kotlin 4단계 신규 |
| 5 | 단절 후 snapshot·sequence·미종결 명령을 대조한다 | `/devices/{id}/sync` | `test_sync_api::*` 5건 | 보존(단, 재부팅 구분은 ADR 0005) / Golden에는 아직 없음 |
| 6 | Command와 Telemetry의 계정·ACL·Stream이 분리된다 | Redis ACL 사용자 2개, 앱 시작·재연결 시 등록 | `test_redis_acl::*` 6건(재시작 복구 회귀 포함) | 보존 |
| 7 | 운용 세션에서 Git SHA·image digest·버전을 역추적할 수 있다 | `deployments`+`operation_sessions` | `test_deployment_api::*`, `test_replay_session::*` | 보존 |
| 8 | 동일 seed로 전환 전후를 Replay 비교할 수 있다 | 시뮬레이터 seed 재현 | Golden Replay(결정성 확인) | 보존(기준선 완료) |

## 5. 요구사항 추적표 (REQ → 시험 → 증거)

TEST-ID 표기: `pytest:<파일>::<함수>`, `golden:<시나리오>`, `contract:<파일>`. "Kotlin 게이트"는 같은
시험을 Kotlin 구현에 돌려 통과해야 한다는 뜻이다.

| REQ-ID | 요구 | 현행 TEST-ID | 증거 | Kotlin 게이트 |
|---|---|---|---|---|
| REQ-TEL-01 | 계약 위반 프레임은 거부(422) | `pytest:test_ingestion_pipeline::test_invalid_frame_rejected_with_422` | pytest | 3단계 |
| REQ-TEL-02 | 중복은 한 번만 저장 | `pytest:…::test_duplicate_frame_not_double_counted`, `golden:duplicate` | Golden 기준선 | 3단계 |
| REQ-TEL-03 | 역순·지연이 최신 상태를 후퇴시키지 않음 | `golden:out_of_order`, `golden:reorder5`, `golden:delay` | Golden 기준선 | 3단계 |
| REQ-TEL-04 | 손실·단절이 있어도 받은 프레임은 전부 보존 | `golden:missing`, `golden:disconnect`, `golden:loss20` | Golden 기준선 | 3단계 |
| REQ-TEL-05 | 부팅이 바뀌어도 새 프레임을 중복으로 버리지 않음 | (없음 → ADR 0005 구현 시 `golden:reboot` 추가) | — | 3단계 |
| REQ-ALR-01 | 배터리·RSSI·지오펜스 경보 발생, 중복 경보 억제 | `pytest:test_alert_pipeline::*`, `golden:battery_low` | Golden(배터리만) | 3~4단계 |
| REQ-CMD-01 | 명령은 승인 후에만 전달 | `pytest:test_command_lifecycle::test_approve_auto_dispatches_when_not_expired`, `golden:success` | Golden 기준선 | 4단계 |
| REQ-CMD-02 | 요청자 본인 승인 금지(403) | `golden:self_approve` | Golden 기준선 | 4단계 |
| REQ-CMD-03 | 같은 idempotency_key 재요청은 명령 1개 | `golden:idempotent` | Golden 기준선 | 4단계 |
| REQ-CMD-04 | 불법 상태 전이 거부(409) | `golden:illegal`, `golden:cancel` | Golden 기준선 | 4단계 |
| REQ-CMD-05 | ACK 누락·만료 시 종결 상태로 수렴 | `golden:ack_lost` | Golden 기준선 | 4단계(UNKNOWN 결정 후 갱신) |
| REQ-CMD-06 | Dispatch 직전 권한·통제권·세션·신선도 재검사 | (없음 — 신규 요구) | — | 4단계 신규 |
| REQ-SYN-01 | 재연결 시 sequence gap·미종결 명령 대조 | `pytest:test_sync_api::*` | pytest | 5단계(Golden 추가 필요) |
| REQ-CHN-01 | Telemetry 계정으로 Command Stream 접근 거부, Redis 재시작 후 복구 | `pytest:test_redis_acl::*` | pytest | 5단계 |
| REQ-TRC-01 | 운용 세션에 배포 버전 고정·역추적 | `pytest:test_deployment_api::*` | pytest | 2·4단계 |
| REQ-RPL-01 | 동일 입력 Replay 결과 결정적 일치 | Golden Replay 2회 연속 일치 | 기준선 | 전 단계 |
| REQ-CTR-01 | REST·WS·Stream 계약 유지 | `contract:tests/contracts/baseline/*` | 드리프트 테스트 | 전 단계 |

## 6. Day 1 이후 처리할 결정·공백

- **ADR 0004·0005 승인**(제안 기본값 포함).
- **Golden 시나리오 추가 후보**: `reboot`(ADR 0005), 재동기화, 운용 세션 재생, PENDING_APPROVAL timeout.
  지오펜스·RSSI 경보는 격리 환경이 필요해 보류.
- **불변조건 3·4번의 진화 방향**: ACK 누락을 `UNKNOWN`으로 유지할지, Dispatch 재검사 항목(권한·통제권·세션·
  신선도·정책)의 범위를 어디까지 둘지 Kotlin 4단계 전에 ADR로 결정.
- **`event_log` 쓰기 경계**(§2)와 **Incident 이관 시점**(§3) 결정.
- `identity` 모듈은 users/roles 테이블이 아직 없다. Kotlin 2단계의 OIDC/RBAC 골격이 사실상 신규 구현이다.
