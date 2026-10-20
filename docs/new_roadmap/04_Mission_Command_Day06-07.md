# 4단계 — Mission·Command & Control (Day 6~7)

## 목표

임무와 명령의 핵심 불변조건을 Kotlin Aggregate로 옮긴다.

## 작업

- Mission·MissionPhase·Route Aggregate 구현
- Command·Approval·ControlLease·EffectVerification 모델 구현
- 요청자·승인자 분리와 고위험 명령 정책
- Dispatch 직전 권한·Lease·Session·만료·Freshness 재검증
- 낙관적 잠금과 idempotency key
- 상태 전이와 Outbox Event 원자성
- ACK·실행·완료·목표 도달 상태 분리
- 단계별 Timeout과 재동기화 Use Case
- 동시 승인·과거 Session·ACK 손실·중복 요청 시험

## 완료 게이트

중복 Command 실행 0건, 불법 상태 전이 0건, 모든 명령 전이와 판단 근거를 Audit에서 재구성할 수 있다.
