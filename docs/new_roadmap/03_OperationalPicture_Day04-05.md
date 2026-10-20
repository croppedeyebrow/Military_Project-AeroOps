# 3단계 — Operational Picture 전환 (Day 4~5)

## 목표

같은 Telemetry를 FastAPI와 Kotlin이 읽고 최신 상태와 데이터 품질을 비교한다.

## 작업

- 외부 Wire DTO→`Observation` Anti-Corruption Layer 구현
- 위치·자세·배터리·통신별 관측·수신 시각 분리
- `KNOWN/STALE/PARTIAL/INVALID/UNKNOWN` 품질 모델
- `(asset_id, boot_id, sequence_no)` 멱등 처리
- Late Event 원본 보존과 Latest Projection 후퇴 방지
- Kotlin Shadow Schema와 Comparator 구현
- 기존 React 계약을 유지하는 Read API·WebSocket Adapter
- 10대×1Hz와 100대×10Hz 탐색 부하 시험

## 완료 게이트

Golden Replay에서 허용 차이 외 최종 상태가 일치하고, 오래된 Event가 최신 상태를 덮어쓰는 사례가 0건이다.
