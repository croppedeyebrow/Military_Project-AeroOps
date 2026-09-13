# AeroOps Frontend

React + TypeScript + Vite. `docs/planning/01_프론트엔드_아키텍처.md` 참고.

## 로컬 실행

4단계부터 실제 backend(WebSocket `/ws/operations`, `GET /assets`)가 필요하다 —
[`backend/README.md`](../backend/README.md)로 backend를 먼저 띄운다.

```bash
npm install
cp .env.example .env
npm run dev
```

## 테스트 / 린트 / 빌드

```bash
npm run lint
npm run build
npm run test
```

## 구조

- `src/components/` — `OperationsMap`, `AssetList`, `AssetDetail`, `ResyncBanner`(4단계
  구현), `Vehicle3DViewer`, `AlertPanel`, `ReplayTimeline`, `TelemetryChart`(이후 단계,
  각 폴더 README 참고)
- `src/store/useOperationsStore.ts` — 실시간 최신 프레임(WebSocket) + 화면 선택(Zustand)
- `src/api/` — TanStack Query 훅(`assets.ts`: 초기 자산 목록, `health.ts`)
- `src/ws/useTelemetryStream.ts` — `/ws/operations` 구독, 지수 백오프 재연결
- `src/types/telemetry.ts` — 백엔드 `TelemetryFrame` 계약과 1:1 대응하는 타입, 신선도
  판정(`classifyFreshness`)

## 실시간 데이터 흐름 (4단계)

`useTelemetryStream`이 연결되면 서버가 전체 기체의 최신 상태 스냅샷을 한 번 보내고,
이후 갱신되는 기체만 스트리밍한다. 연결이 끊기면 지수 백오프로 재연결하고, 재연결
성공 시 서버가 또 새 스냅샷을 보내주므로 별도 "resume" 프로토콜 없이 최신 상태로
복구된다(`ResyncBanner`가 재연결을 잠깐 알려준다). WebSocket이 연결되기 전이나 실패
시에는 `GET /assets`(TanStack Query)로 조회한 값이 화면을 먼저 채운다.

## 지도 스타일

기본값은 API 키가 필요 없는 공개 데모 스타일이다. 실제 배포 시 `.env`의
`VITE_MAP_STYLE_URL`을 MapTiler 등 실제 벡터 타일 스타일 URL로 바꾼다.
