# Telemetry 모듈

책임: 최신 상태와 기간별 이력 조회.

- `GET /assets/{id}/latest`
- `GET /assets/{id}/telemetry`

3단계에서 `asset_latest_state`, `telemetry_frames` 테이블 기반으로 구현한다
(`docs/roadmap/03_단계_수집저장파이프라인_Day0507.md`). 7단계에서 이력 재생을
위한 페이지·다운샘플링을 추가한다.
