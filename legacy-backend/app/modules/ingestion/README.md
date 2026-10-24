# Ingestion 모듈

책임: 스키마·범위 검증, 이벤트 발행 (`POST /telemetry`).

## 구현 (3단계 완료)

- `router.py` — `POST /telemetry`: FastAPI가 `TelemetryFrame`으로 요청 본문을 검증하고
  (실패 시 422, `aeroops_telemetry_rejected_total` 증가), `received_at`을 서버 시각으로
  채운 뒤 Redis Stream(`aeroops:telemetry:raw`)에 발행하고 202를 반환한다.
- `streams.py` — 스트림 이름·소비자 그룹 상수(`telemetry` 모듈의 consumer와 공유).

실제 저장·중복 판정·최신 상태 갱신은 이 모듈이 아니라 `app.modules.telemetry.consumer`가
비동기로 수행한다(`docs/planning/02_백엔드_아키텍처.md`: "오래 걸리는 분석을 요청 경로에서
실행하지 않는다").
