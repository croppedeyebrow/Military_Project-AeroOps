# CommandEnvelope 데이터 사전

`backend/app/schemas/command.py`와 `simulator/simulator/contracts/command.py`가 구현하는
공유 계약. 동기화 방식은 [ADR 0002](../decisions/0002-telemetry-contract-duplication.md)와
동일한 원칙(Docker 빌드 컨텍스트 분리 → 계약 독립 구현 + 데이터 사전 SSOT)을 따른다.

## TelemetryFrame과의 관계

`docs/planning/02_백엔드_아키텍처.md` "채널 및 권한 분리": Telemetry는 기체→서버 단방향
고빈도 데이터이며 유실 허용 정책을 가지고, Command는 서버→기체 저빈도 제어 의도이며 인증·
승인·ACK·감사 추적이 필수다. 두 계약은 **필드 집합이 겹치지 않아**, 한쪽 계약으로 다른 쪽
데이터를 검증하면 필수 필드 누락으로 항상 실패한다 — 별도의 "채널 분리 검증 로직"을 추가하지
않아도 계약 자체가 분리를 강제한다.

## 필드

| 필드 | 타입 | 범위/제약 | 필수 | 설명 |
|---|---|---|---|---|
| `schema_version` | int | ≥1, 기본 1 | ✓ | 계약 버전. |
| `command_id` | str | 공백 불가 | ✓ | 명령 고유 식별자. |
| `idempotency_key` | str | 공백 불가 | ✓ | 같은 키로 재요청해도 명령이 하나만 생성됨을 보장하는 키(3단계 보정에서 DB 유일 제약으로 강제). |
| `target_asset_id` | str | 공백 불가 | ✓ | 대상 기체(`TelemetryFrame.asset_id`와 동일 식별자 체계). |
| `command_type` | str | 공백 불가 | ✓ | 명령 종류(예: `RTL`, `SET_MISSION`, `ARM`, `DISARM`). 구체적인 값 집합은 5단계에서 `command` 모듈이 검증한다. |
| `payload` | dict | 기본 `{}` |  | 명령별 파라미터(JSON 직렬화 가능한 값). |
| `requested_by` | str | 공백 불가 | ✓ | 요청자(사용자 ID). |
| `approved_by` | str \| null | - |  | 승인자. 요청자와 분리(`docs/planning/01_프론트엔드_아키텍처.md` "안전한 명령 UX"). |
| `issued_at` | datetime | UTC | ✓ | 명령 발급 시각. |
| `expires_at` | datetime | UTC, `issued_at` 이후 | ✓ | 만료 시각. 만료된 명령은 dispatch하지 않는다. |
| `expected_asset_state_version` | int \| null | ≥0 |  | 이 명령이 전제하는 기체 상태 버전(낙관적 동시성 — 재동기화 시 대조). |
| `deployment_id` | str \| null | - |  | 이 명령을 발급한 배포 버전(7단계 이벤트 추적). |

## 상태 머신 (계약 밖, `command` 모듈이 관리)

```
DRAFT → PENDING_APPROVAL → APPROVED → DISPATCHED → ACKNOWLEDGED → EXECUTING
  → SUCCEEDED / FAILED / TIMED_OUT / CANCELLED
```

`CommandEnvelope` 자체는 상태를 갖지 않는 불변 스펙이다. 상태 이력은 `command_events`
테이블(3단계 보정에서 migration 추가, 5단계에서 상태 머신 로직 완성)이 담당한다.

## 예제

```json
{
  "schema_version": 1,
  "command_id": "cmd-0001",
  "idempotency_key": "op-console-2026-09-13-0001",
  "target_asset_id": "drone-01",
  "command_type": "RTL",
  "payload": {},
  "requested_by": "operator-1",
  "approved_by": "supervisor-1",
  "issued_at": "2026-09-13T00:00:00Z",
  "expires_at": "2026-09-13T00:05:00Z",
  "expected_asset_state_version": 42,
  "deployment_id": null
}
```
