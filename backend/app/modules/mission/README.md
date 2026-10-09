# Mission 모듈

책임: 임무·경로·구역·상태 전이 (`/missions`, `/geofences`).

## 구현 (5단계 완료)

- `models.py` — `Mission`(임무명·상태·시작·종료), `MissionRoute`(예정 경로, 재계획을
  append-only로 기록해 항상 최신 것을 "현재 경로"로 씀), `Geofence`(구역 유형·Polygon).
- `repository.py`, `router.py` — `POST/GET/PATCH /missions`, `PUT/GET
  /missions/{id}/route`, `POST/GET /geofences`.
- 좌표는 GeoJSON 관례([경도, 위도] 순서)의 평문 JSONB로도 저장해 프론트가 바로 지도에
  그릴 수 있게 하고, PostGIS geometry 컬럼도 함께 둔다(공간 질의 대비).
- `alert` 모듈이 `list_geofences`를 그대로 재사용해 지오펜스 이탈 판정에 쓴다.

## 로드맵

임무 상태(`PLANNED/ACTIVE/COMPLETED/ABORTED`)를 텔레메트리·명령과 자동으로 연결하는
로직(예: 임무 시작 시 관련 기체 자동 배정)은 아직 없다 — 필요해지면 이후 단계에서
추가한다.
