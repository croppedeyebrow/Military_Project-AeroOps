# ReplayTimeline

이력 재생 구간·배속(0.5x/1x/2x)·일시정지·탐색 컨트롤. 지도·3D·차트를 동일
timestamp로 동기화한다. 7단계(`docs/roadmap/07_단계_이력재생_관측성_Day16-18.md`)에서
구현. 사용자 결정(2026-10-11): 재생 구간은 운용 세션 목록에서 고르고, 재생 화면은
실시간 관제와 분리된 별도 탭이다.

## 화면 구성 (Unit 4)

- `ReplayScreen.tsx`: "이력 재생" 탭 전체. 고른 세션 구간의 기체별 이력을 한 번만
  받아(`useReplayDatasetQuery`) 하위 재생 화면에 `dataset` prop으로 내려준다. 재생 대상
  배포는 `DeploymentBadge deploymentId=...`로 표시.
- `ReplayTimeline.tsx`: 컨트롤 바 — 세션 드롭다운, 재생/일시정지, 배속 0.5×/1×/2×,
  1초 단위 스크럽 슬라이더, "경과/전체 · 절대시각" 라벨. `useReplayClockLoop`를 여기서
  마운트해 재생 탭에 있을 때만 시계가 돈다.
- `format.ts`: `sessionRange`(진행 중 세션은 "선택한 순간의 지금"을 끝으로, 최소 1초 폭
  보장), `formatDuration`/`formatReplayClock`.
- 지도·3D·상세는 모두 같은 `useReplayStore.currentTimeMs`를 읽어 그리므로, 별도 동기화
  코드 없이 같은 시각을 가리킨다(완료 기준 "같은 timestamp에서 값 일치"를 구조로 보장).

## 기반 조각 (Unit 1~3)

- `frameLookup.ts`: 이분 탐색으로 "그 시각 이전 가장 최근 프레임" 탐색
  (`findFrameAtTime`), 기체별 이력 묶음(`ReplayDataset`)에서 "지금(재생 커서) 보여줄
  기체별 프레임"을 한 번에 만드는 `buildAssetFramesAtTime`.
- `useReplayClockLoop.ts`: 재생 중일 때만 도는 `requestAnimationFrame` 루프 —
  `store/useReplayStore.ts`의 `tick()`을 몬다.
- `ReplayMap.tsx` / `ReplayVehicle3DViewer.tsx` / `ReplayAssetDetail.tsx`: 실시간
  관제의 `OperationsMap`/`Vehicle3DViewer`/`AssetDetail`과 **같은 렌더링 로직**
  (`OperationsMapView`/`Vehicle3DViewerView`/`AssetDetailView`)을 재사용하는 재생 전용
  얇은 래퍼. 데이터는 `useReplayStore`(재생 커서·선택 기체)와 `dataset` prop(기체별
  이력, `api/replay.ts`의 `useReplayDatasetQuery`로 받아온 것)에서 가져온다.

## 의도적으로 하지 않은 것

- `ReplayMap`은 임무 경로·구역 폴리곤을 보여주지 않는다 — "현재" 임무/구역만 조회
  가능해서, 재생 중에 보여주면 그 시절엔 없었을 정보처럼 혼동을 줄 수 있다.
- `ReplayVehicle3DViewer`/`ReplayAssetDetail`은 신선도(live/stale) 표시와 "최근 연관
  명령" 배지를 보여주지 않는다 — 둘 다 "지금(실제 현재 시각)"을 전제로 한 개념인데
  재생 중엔 "지금"이 재생 커서 시각이라 그대로 쓰면 틀린 정보가 된다.

- 세션을 고르면 기체 수만큼 `GET /assets/{id}/telemetry`를 호출한다 — MVP 규모(10대)
  에선 문제없지만, 기체가 수백 대로 늘면 여러 기체 이력을 한 번에 주는 배치 endpoint가
  필요하다(테스트 DB처럼 기체가 150대 넘게 쌓인 환경에선 요청이 그만큼 늘어난다).

## 아직 없는 것 (다음 단위)

- `TelemetryChart`: 배터리 등 시계열 차트 + 커서 동기화(Unit 5).
- 재생 중 경보·명령 이벤트 마커(`GET /operation-sessions/{id}/replay`의 event_log 활용).
