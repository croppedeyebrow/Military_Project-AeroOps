import { create } from "zustand";

/**
 * 화면 선택·레이어 상태 (Zustand).
 * `docs/planning/01_프론트엔드_아키텍처.md`의 상태 관리 규칙: 서버 데이터는
 * TanStack Query, 실시간 최신 프레임은 WebSocket 전용 store, 화면
 * 선택/레이어는 Zustand, 재생 시각/배속은 Replay Controller가 담당한다.
 */
interface OperationsState {
  selectedAssetId: string | null;
  selectAsset: (assetId: string | null) => void;
}

export const useOperationsStore = create<OperationsState>((set) => ({
  selectedAssetId: null,
  selectAsset: (assetId) => set({ selectedAssetId: assetId }),
}));
