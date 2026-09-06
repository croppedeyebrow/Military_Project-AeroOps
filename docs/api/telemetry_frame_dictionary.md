# TelemetryFrame 데이터 사전

`backend/app/schemas/telemetry.py`와 `simulator/simulator/contracts/telemetry.py`가 구현하는
공유 계약. 두 구현을 동기화하는 방법은 [ADR 0002](../decisions/0002-telemetry-contract-duplication.md) 참고.

## 공통 규칙

- 모든 시각은 **UTC**, ISO 8601(`datetime`)로 표현한다.
- 위치는 **WGS84**(위경도, 도 단위), 고도는 **지면 기준 미터(m)**.
- 각도는 모두 **도(degree)** 단위.
- `schema_version`이 다르면 검증 전에 마이그레이션 또는 거부한다.

## 필드

| 필드 | 타입 | 단위/범위 | 필수 | 설명 |
|---|---|---|---|---|
| `schema_version` | int | ≥1, 기본 1 | ✓ | 계약 버전. 필드 추가/의미 변경 시 증가. |
| `asset_id` | str | 공백 불가 | ✓ | 기체 식별자(호출부호와 별개인 내부 ID). |
| `mission_id` | str \| null | - |  | 현재 배정된 임무. 미배정 시 `null`. |
| `event_time` | datetime | UTC | ✓ | 기체(시뮬레이터)가 프레임을 생성한 시각. |
| `received_at` | datetime \| null | UTC, `event_time` 이상 |  | 서버가 수신한 시각. 시뮬레이터는 보통 비워 보내고 수집 API가 채운다. |
| `sequence_no` | int | ≥0 | ✓ | 기체별 단조 증가 카운터. `(asset_id, sequence_no)`로 중복 판정(`03_데이터베이스_아키텍처.md`). |
| `latitude` | float | [-90, 90] | ✓ | WGS84 위도. |
| `longitude` | float | [-180, 180] | ✓ | WGS84 경도. |
| `altitude_m` | float | [-500, 10000] | ✓ | 지면 기준 고도(m). |
| `speed_mps` | float \| null | [0, 150] |  | 지면 속도(m/s). |
| `heading_deg` | float \| null | [0, 360) |  | **지면 진행 방향**(ground track). 0=N, 90=E, 시계방향. |
| `roll_deg` | float \| null | [-180, 180] |  | 기체 롤. 우측으로 기울면 양수. |
| `pitch_deg` | float \| null | [-90, 90] |  | 기체 피치. 기수가 위로 들리면 양수. |
| `yaw_deg` | float \| null | [-180, 180] |  | **기수 방향**(body heading). `heading_deg`와 별개 개념(옆바람 시 다를 수 있음). |
| `battery_pct` | float | [0, 100] | ✓ | 배터리 잔량(%). |
| `rssi_dbm` | float \| null | [-130, 0] |  | 통신 신호 강도(dBm). |
| `flight_mode` | enum \| null | `MANUAL`\|`AUTO`\|`GUIDED`\|`LOITER`\|`RTL`\|`LANDED` |  | 비행 모드. |

## heading vs yaw

`heading_deg`는 지면에 대한 실제 이동 방향(예: 옆바람에 밀리는 경우 기수 방향과 달라짐)이고,
`yaw_deg`는 기체 기수가 향하는 방향이다. 시뮬레이터의 기본 시나리오(무풍 가정)에서는 두 값이
일치하지만, 계약과 화면(지도 아이콘 vs 3D 자세)에서는 항상 구분해서 다룬다
(`docs/planning/01_프론트엔드_아키텍처.md`, `docs/planning/05_데이터엔지니어링_아키텍처.md`
"일관성" 규칙).

## 예제

정상 프레임과 오류 유형별 예제는 [`docs/api/examples/`](examples/)에 있다.

## 장애 시나리오와의 관계

시뮬레이터가 주입하는 장애(2단계, `simulator/simulator/faults.py`)는 이 계약 자체를 어기지 않는
"운영상 이상"과, 계약을 어기는 "계약 위반"으로 나뉜다.

| 장애 유형 | 계약 위반 여부 | 표현 방식 |
|---|---|---|
| 중복(duplicate) | 아니오 | 동일 `(asset_id, sequence_no)` 프레임을 한 번 더 내보냄 |
| 지연(delay) | 아니오 | `event_time`은 그대로 두고 실제 전송/도착을 늦춤 |
| 역순(out_of_order) | 아니오 | 프레임 전송 순서를 `sequence_no` 오름차순과 다르게 섞음 |
| 결측(missing) | 아니오 | 특정 `sequence_no` 프레임을 전송하지 않고 건너뜀 |
| GPS 점프(gps_jump) | 아니오(값 자체는 유효 범위) | 위경도를 물리적으로 불가능한 거리만큼 순간 이동 |
| 통신 단절(disconnect) | 아니오 | 한 기체의 프레임 구간 전체가 비는 공백 구간 생성 |
| 배터리 급락(battery_drop) | 아니오 | 짧은 시간 내 `battery_pct`가 비정상적으로 급락 |

모든 장애는 계약(`TelemetryFrame` 필드 범위) 자체는 지키도록 설계한다 — 계약 위반은 별도로
"잘못된 프레임 거부" 테스트(범위를 벗어난 위경도·배터리·각도)로 검증한다.
