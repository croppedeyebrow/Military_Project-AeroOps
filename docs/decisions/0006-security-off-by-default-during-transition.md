# ADR 0006: 전환 기간 동안 Kotlin C2 Core의 인증을 기본 비활성으로 둔다

- 상태: 제안됨 (사용자 승인 전)
- 일자: 2026-10-28
- 관련: [ADR 0004](0004-strangler-transition-to-kotlin-c2-core.md)(Strangler 전환), `docs/new_roadmap/02`(2단계 Security 골격), `docs/new_roadmap/08`(8단계 mTLS·identity)

## 배경

2단계 계획에는 "Spring MVC, Validation, Security OIDC/JWT 골격"이 있다. 그런데 보안을 실제로 켜면
전환 전략과 충돌하는 지점이 있다.

1. **legacy에는 인증이 전혀 없다.** `legacy-backend`의 `identity` 모듈은 README만 있는 껍데기이고,
   users·roles 테이블도 없다(`docs/planning/13` §6). 실제 인증은 8단계 과제다.
2. **전환 판정은 "같은 계약"에 달려 있다.** Golden Replay(`tests/contracts/replay/run_golden_replay.py`)는
   HTTP로 legacy와 Kotlin에 **같은 요청**을 보내 결과를 비교한다. 계약 기준선(`tests/contracts/baseline`)도
   인증 없는 요청을 전제로 고정돼 있다.
3. Kotlin만 인증을 요구하면 같은 시험을 돌릴 수 없다. 즉 **보안을 켜는 순간 전환 비교 수단을 잃는다.**

## 결정

**인증·인가 인프라는 만들되, 기본 설정에서는 어떤 경로도 보호하지 않는다.**

- 스위치: `aeroops.security.enabled` (기본 `false`). 켜면 헬스 엔드포인트를 뺀 모든 요청에 유효한 JWT를 요구한다.
- 메서드 보안(`@PreAuthorize`)도 **같은 스위치**로 함께 켜진다(`MethodSecurityConfig`). 따로 두면 필터체인이
  비보호인데 메서드에서 막히는 어긋남이 생긴다.
- 역할은 `OperationalRole`(OPERATOR·APPROVER·ANALYST·ADMIN)로 타입화해 Identity & Audit 컨텍스트가 소유한다.
- JWT의 `roles` 클레임을 권한으로 변환하며, 모르는 역할 문자열은 무시한다(요청 전체를 실패시키지 않는다).

### 이 결정의 위험과 대비

가장 큰 위험은 **"보안을 넣었다"는 착각**이다. 코드가 있지만 실제로는 아무것도 보호하지 않는 상태를
누군가 "보안 구현 완료"로 읽을 수 있다. 그래서:

1. 기본이 비보호임을 설정 이름·주석·이 ADR에 명시한다.
2. **켰을 때 실제로 막히는지**를 시험으로 증명한다(`SecurityEnabledTest`: 토큰 없으면 401, 역할이 다르면 403,
   모르는 역할만 있으면 403). 이 시험이 없으면 보안 코드가 동작하지 않아도 아무도 모른다.
3. **꺼졌을 때 열려 있는 것도** 시험으로 고정한다(`SecurityDisabledTest`). 누군가 기본값을 바꾸면 실패한다.

## 켜는 시점

| 조건 | 내용 |
|---|---|
| 선행 | 실제 OIDC 공급자 연동(발급자·JWK) — 8단계 |
| 선행 | React가 토큰을 붙여 보내도록 수정 — 현재 `frontend/src/api/client.ts`는 토큰을 보내지 않는다 |
| 선행 | Golden Replay 실행기가 토큰을 붙이도록 수정(또는 시험 전용 우회 경로 합의) |
| 판단 | 위 셋이 갖춰지기 전에 켜면 전환 비교가 깨진다 |

## 대안과 기각 이유

- **처음부터 보안을 켠다**: 전환 비교 수단(Golden Replay)을 잃는다. 또한 legacy에 없는 401/403이 생겨
  프론트 계약도 깨진다.
- **보안 코드를 아예 만들지 않는다**: 8단계에 가서야 구조를 처음 고민하게 된다. 역할 어휘·권한 변환 지점을
  미리 정해 두면 이후 컨텍스트들이 같은 규칙 위에서 자란다.
- **경로별로 일부만 보호한다**: 어떤 경로가 보호되는지 사람이 기억해야 하고, Golden Replay가 그 경로를
  건드리는 순간 조용히 깨진다. 스위치 하나로 전부/전무를 택하는 편이 상태가 분명하다.

## 영향

- 전환 기간의 Kotlin API는 **인증 없이 접근된다**. 외부에 노출하지 않는 것을 전제로 한다(현재는 로컬·내부망).
- 8단계에서 이 ADR을 대체하는 결정(실제 공급자·mTLS·프론트 토큰)을 새로 남긴다.

## 연관 코드

- `backend/bootstrap/src/main/kotlin/com/aeroops/c2/SecurityConfig.kt` (필터체인·역할 변환, `MethodSecurityConfig`)
- `backend/audit/src/main/kotlin/com/aeroops/c2/audit/OperationalRole.kt` (역할 정의)
- `backend/bootstrap/src/test/kotlin/com/aeroops/c2/SecurityConfigTest.kt` (켜짐·꺼짐 두 상태 시험)
