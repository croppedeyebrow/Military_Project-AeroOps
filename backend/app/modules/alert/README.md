# Alert 모듈

책임: 배터리·통신·지오펜스 규칙 판정 (`/alerts`).

## 구현 (5단계 완료)

- `rules.py` — 순수 함수 규칙 3종: `evaluate_battery`(경고 20%/위험 10%),
  `evaluate_rssi`(경고 -100dBm), `evaluate_geofence`(PROHIBITED 구역 진입, ray-casting).
  `RULE_VERSION`을 올리면 이후 생성되는 경보부터 새 버전이 찍힌다.
- `repository.py` — `evaluate_and_raise_alerts`가 `telemetry` consumer에서 최신 상태가
  갱신될 때마다 호출된다(`app/modules/telemetry/consumer.py`). 같은 `asset_id`+
  `alert_type`의 `OPEN` 경보가 이미 있으면 새로 만들지 않는다(중복 방지) — 확인
  (`acknowledge`)·해제(`resolve`) 상태 전이.
- `router.py` — `GET /alerts`(상태·기체 필터), `POST /alerts/{id}/acknowledge`,
  `POST /alerts/{id}/resolve`. 경보 생성 자체는 사용자 API가 아니라 파이프라인이 한다.
- 새 경보는 `/ws/operations`에 `{"type": "alert", ...}`로도 실시간 브로드캐스트된다
  (`app/modules/realtime/broadcaster.py`).

## 알려진 제한

- 지오펜스 판정은 매 프레임마다 전체 지오펜스 목록을 DB에서 다시 읽는다(구역 수가
  적은 MVP 규모에서는 문제없다) — 늘어나면 캐싱을 고려한다.
