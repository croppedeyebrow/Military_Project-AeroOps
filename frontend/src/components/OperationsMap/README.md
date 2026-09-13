# OperationsMap

MapLibre 기반 2D 관제 지도. 전체 드론 방향 아이콘·호출부호·상태 색상, 실제 이동 경로
(실선)를 표시한다. 예정 경로(점선)·구역 폴리곤은 5단계에서 레이어를 추가한다.

## 구현 (4단계)

- 별도 API 키가 필요 없는 공개 데모 스타일(`https://demotiles.maplibre.org/style.json`)을
  기본값으로 쓴다 — `VITE_MAP_STYLE_URL`로 실제 벡터 타일 스타일로 교체 가능.
- 방향 아이콘은 스프라이트 이미지 대신 CSS 삼각형(`markerElement.ts`)으로 그린다 —
  `heading_deg`만큼 회전(0=N, 시계방향)하고, 신선도(`live`/`stale`/`disconnected`)에 따라
  색이 바뀐다. 단절 시 마커 옆에 기체 ID와 경과 시간(`format.ts`)을 라벨로 보여준다.
- 실제 이동 경로는 세션 동안의 최근 위치만 짧게 유지한다(`trails.ts`, 최대
  `TRAIL_MAX_POINTS`개) — 장기 이력을 브라우저에 쌓지 않는다는 원칙
  (`docs/planning/01_프론트엔드_아키텍처.md`)을 그대로 따른다. 전체 비행 이력 재생은
  7단계 `ReplayTimeline`의 몫이다.
- `markerElement.ts`, `format.ts`, `trails.ts`는 순수 함수/DOM 조작이라 MapLibre 없이도
  단위 테스트한다(`*.test.ts`).
