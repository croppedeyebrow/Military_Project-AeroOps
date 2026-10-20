# Rust 통신·Edge 기술

## 적용 위치

Edge Agent와 Device Gateway에서 장비 연결, mTLS, Frame 검증, QoS, Store-and-Forward와 재접속을 담당한다.

## 공부할 개념

- Ownership, Borrowing, Lifetime, Result/Error
- Tokio Task, async I/O, cancellation
- TCP/TLS, framing, heartbeat, timeout
- bounded channel, backpressure, load shedding
- X.509, mTLS, SAN, 인증서 폐기
- nonce, sequence, expiry, Replay 방지
- store-and-forward, reconnect backoff+jitter
- property test와 fuzzing

## 적용 원칙

- Command와 Telemetry의 listener·Credential·Queue를 분리한다.
- 일반 Telemetry는 병합할 수 있지만 Command 상태 Event는 병합하지 않는다.
- 업무 규칙은 Rust Gateway에 복제하지 않는다.
- 모든 외부 Frame은 Kotlin Domain 진입 전 ACL에서 변환한다.

## 실습

Telemetry 폭주와 집단 재접속 중 Command p95, Queue 깊이, Drop 수와 메모리 사용량을 측정한다.
