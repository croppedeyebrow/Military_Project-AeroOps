# Ingestion 모듈

책임: 스키마·범위 검증, 중복 판별, 이벤트 발행 (`POST /telemetry`).

- 2단계: `TelemetryFrame` 계약 검증 연결
- 3단계: Redis Streams producer, `asset_id + timestamp + sequence`
  중복 판정 구현 (`docs/roadmap/03_단계_수집저장파이프라인_Day0507.md`)

## 예정 구성

- `router.py` — `POST /telemetry`
- `service.py` — 검증·중복 판정 로직
- `producer.py` — Redis Streams 발행
