# Audit 모듈

책임: 중요 명령과 설정 변경 기록 (행위자·행동·대상·결과·시각).

## 구현 (5단계 완료)

- `models.py` — `AuditLog`(append-only).
- `repository.py` — `record_audit_event(db, actor, action, target_type, target_id, ...)`.
  공통 데코레이터/미들웨어 대신 각 모듈이 주요 행위 직후 명시적으로 호출한다 — 호출
  지점이 몇 곳 안 되는 규모에서는 이쪽이 더 읽기 쉽다고 판단했다(자세한 이유는
  `repository.py` docstring).
- `router.py` — `GET /audit-logs`(target_type/target_id 필터). 인증은 8단계에서 적용.
- 현재 기록 지점: `mission.create/update/set_route`, `geofence.create`,
  `command.create/approve/cancel`, `alert.acknowledge/resolve`.

## 알려진 제한

- 주 작업과 감사 기록이 완전한 outbox 트랜잭션으로 묶여 있지 않다(주 작업 커밋 직후
  별도 커밋) — 두 커밋 사이 크래시 시 감사 기록만 유실될 수 있다(극히 드묾).
- 8단계 전까지는 `actor`가 인증되지 않은 고정값(`operator` 등)이다.
