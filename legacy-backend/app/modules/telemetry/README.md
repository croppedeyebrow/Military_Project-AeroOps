# Telemetry 모듈

책임: 원본 저장·최신 상태 갱신(consumer), 최신 상태와 기간별 이력 조회(API).

## 구현 (3단계 완료)

- `models.py` — `Asset`, `TelemetryFrameRecord`(원본, 불변), `AssetLatestState`(기체별 최신
  정상 프레임 1건). `docs/planning/03_데이터베이스_아키텍처.md` 참고.
- `repository.py` — DB 접근 계층(동기 SQLAlchemy). `(asset_id, sequence_no)` 유일 제약으로
  중복을 판정하고, `event_time`이 기존 최신 상태보다 새로울 때만 `asset_latest_state`를
  갱신한다(역순 데이터가 최신 상태를 후퇴시키지 않음).
- `consumer.py` — Redis Streams consumer group. 앱 lifespan 동안 백그라운드 asyncio task로
  떠서 `aeroops:telemetry:raw`를 소비해 `repository`로 반영한다.
- `router.py` — `GET /assets/{id}/latest`, `GET /assets/{id}/telemetry`(기간·페이지네이션).
- `schemas.py` — DB 레코드 → `TelemetryFrame` 응답 변환.

7단계에서 이력 재생을 위한 다운샘플링을 추가한다.
