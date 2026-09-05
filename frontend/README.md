# AeroOps Frontend

React + TypeScript + Vite. `docs/planning/01_프론트엔드_아키텍처.md` 참고.

## 로컬 실행

```bash
npm install
cp .env.example .env
npm run dev
```

## 구조

- `src/components/` — OperationsMap, AssetList, AssetDetail, Vehicle3DViewer,
  AlertPanel, ReplayTimeline, TelemetryChart (각 폴더 README 참고)
- `src/store/` — Zustand (화면 선택/레이어)
- `src/api/` — TanStack Query 훅
- `src/ws/` — WebSocket 전용 store
- `src/types/` — 백엔드 계약과 대응하는 타입
