# Vehicle3DViewer

선택 기체만 Three.js로 표현하고 roll·pitch·yaw를 실시간 자세에 반영한다. 6단계
(`docs/roadmap/06_단계_3D상세뷰어_Day14-15.md`)에서 구현.

## 파일

- `attitude.ts`: `roll_deg`/`pitch_deg`/`heading_deg` → three.js 쿼터니언 변환 순수 함수.
  좌표축·부호 규칙은 [`docs/decisions/0003-vehicle-3d-axis-convention.md`](../../../../docs/decisions/0003-vehicle-3d-axis-convention.md)
  참고. WebGL 없이 vitest로 검증(`attitude.test.ts`).
- `buildDroneMesh.ts`: 저폴리곤 쿼드콥터 placeholder 지오메트리(박스+실린더 암+원판
  프로펠러)를 코드로 생성. **실제 GLB 모델은 아직 적용하지 않았다** — 사용자 결정
  (2026-10-10)으로 라이선스가 확인된 GLB를 추후 교체 투입하기로 했고, 지금은 외부 에셋
  의존 없이 자세 반영·UI를 먼저 완성한다. GLB 교체 시 이 함수의 반환 그룹만 로더 결과로
  바꾸면 된다(기수가 로컬 `-Z`를 향하도록 배치하는 ADR 0003 규칙 유지 필요).
- `guides.ts`: 진행방향(ground track, heading만)과 기수/센서 방향(전체 자세) 화살표
  보조선. 시뮬레이터가 `yaw_deg == heading_deg`로 생성해 현재는 거의 겹친다.
- `Vehicle3DErrorBoundary.tsx`: 3D 렌더 실패가 2D 관제를 중단시키지 않도록 분리.
- `Vehicle3DViewer.tsx`: 렌더러/씬/카메라는 마운트 시 1회 생성, 기체 선택이 바뀔 때만
  drone 메시를 dispose 후 재생성, 텔레메트리 갱신 시 쿼터니언만 갱신하고 1프레임 렌더
  (60fps 루프 없음 — 텔레메트리가 ~1Hz라 불필요).

## 신선도·명령 연결

- `classifyFreshness`(`types/telemetry.ts`)로 STALE/통신 단절 상태를 판정해 자세값이
  오래됐을 수 있음을 텍스트로 표시한다(오래된 값이 실시간처럼 보이지 않게).
- `api/commands.ts`의 `useAssetCommandsQuery`로 선택 기체의 최근 명령을 조회해 뷰어
  하단에 "최근 연관 명령" 배지로 표시한다(명령 실행 전후 자세 변화를 `command_id`와
  연결해 보여주는 완료 기준).

## 의도적으로 하지 않은 것

- GLB 로딩/로딩중 상태: 현재 지오메트리가 동기 생성이라 실제 비동기 로딩이 없다. GLB
  교체 시 `GLTFLoader`의 `onProgress`/`onError`를 받아 로딩/오류 상태를 추가한다.
- 카메라 조작(OrbitControls): MVP 범위 밖 — 고정 시점 하나로 자세 확인에는 충분하다.
- 창 크기 변화 대응(resize observer): 뷰어가 고정 폭 우측 패널 안에 있어 실익이 적다.
