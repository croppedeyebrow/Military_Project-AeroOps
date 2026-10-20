# 5단계 — Rust 통신 경계 (Day 8~9)

## 목표

장비 연결·Frame 검증·QoS를 C2 Core 밖으로 격리한다.

## 작업

- Tokio 기반 Device Gateway와 Edge Agent 최소 구현
- Command·Telemetry listener, Credential, bounded queue 분리
- 기체 인증서 Subject/SAN–Asset ID 매핑
- Schema Version, Frame 크기, Sequence, Nonce, Expiry 검사
- Command 우선 Queue와 Telemetry Drop·Coalescing
- Store-and-Forward 한도와 폐기 우선순위
- 재접속 Backoff/Jitter와 Snapshot Handshake
- malformed frame fuzzing과 인증서·Replay 부정 시험

## 완료 게이트

Telemetry 폭주 중에도 Command 지연 목표를 만족하고, 무효 인증서·Replay·만료 Command가 모두 차단된다.
