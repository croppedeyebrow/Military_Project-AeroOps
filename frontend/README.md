# AeroOps Frontend

React + TypeScript + Vite. `docs/planning/01_프론트엔드_아키텍처.md` 참고.

## 로컬 실행

4단계부터 실제 backend(WebSocket `/ws/operations`, `GET /assets`)가 필요하다 —
[`legacy-backend/README.md`](../legacy-backend/README.md)로 backend를 먼저 띄운다.

```bash
yarn install
cp .env.example .env
yarn dev
```

## 테스트 / 린트 / 빌드

```bash
yarn lint
yarn build
yarn test
```

## 구조

- `src/components/` — `OperationsMap`, `AssetList`, `AssetDetail`, `ResyncBanner`(4단계),
  `AlertPanel`, `CommandComposer`, `ApprovalQueue`, `CommandTimeline`(5단계),
  `Vehicle3DViewer`, `ReplayTimeline`, `TelemetryChart`(이후 단계, 각 폴더 README 참고)
- `src/store/useOperationsStore.ts` — 실시간 최신 프레임·경보(WebSocket) + 화면 선택(Zustand)
- `src/api/` — TanStack Query 훅(`assets.ts`, `alerts.ts`, `commands.ts`, `missions.ts`,
  `health.ts`), `client.ts`(공통 fetch 래퍼)
- `src/ws/useTelemetryStream.ts` — `/ws/operations` 구독, 지수 백오프 재연결
- `src/types/` — 백엔드 계약과 1:1 대응하는 타입(`telemetry.ts`, `alert.ts`, `command.ts`,
  `mission.ts`), 신선도 판정(`classifyFreshness`)

## 실시간 데이터 흐름 (4~5단계)

`useTelemetryStream`이 연결되면 서버가 전체 기체 최신 상태 + 미확인 경보 스냅샷을 한 번
보내고, 이후 갱신되는 기체·새 경보만 스트리밍한다. 연결이 끊기면 지수 백오프로
재연결하고, 재연결 성공 시 서버가 또 새 스냅샷을 보내주므로 별도 "resume" 프로토콜 없이
최신 상태로 복구된다(`ResyncBanner`가 재연결을 잠깐 알려준다). WebSocket이 연결되기
전이나 실패 시에는 `GET /assets`(TanStack Query)로 조회한 값이 화면을 먼저 채운다.

명령(Command) 채널은 WS로 직접 보내지 않는다 — Command 스트림은 기체 dispatch 전용이라,
프론트는 `ApprovalQueue`가 `GET /commands?status=PENDING_APPROVAL`을 3초 간격 폴링하고,
`CommandTimeline`이 선택한 명령의 `GET /commands/{id}`를 폴링한다.

## 지도 스타일

기본값은 API 키가 필요 없는 공개 데모 스타일이다. 실제 배포 시 `.env`의
`VITE_MAP_STYLE_URL`을 MapTiler 등 실제 벡터 타일 스타일 URL로 바꾼다.
