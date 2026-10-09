import { create } from "zustand";
import type { Alert } from "../types/alert";
import type { TelemetryFrame } from "../types/telemetry";

/**
 * 실시간 최신 프레임·경보 + 화면 선택 상태 (Zustand).
 *
 * `docs/planning/01_프론트엔드_아키텍처.md`의 상태 관리 규칙: 서버 데이터는 TanStack
 * Query, 실시간 최신 프레임은 WebSocket 전용 store, 화면 선택/레이어는 Zustand가
 * 담당한다 — 여기서는 실시간 최신 프레임과 화면 선택을 같은 store에 둔다(둘 다 "지금
 * 화면에 뭘 보여줄지"에 관한 것이라 분리할 이유가 적다).
 *
 * 장기 이력을 쌓지 않는다 — 기체당 "가장 최근 프레임 하나"만 유지한다. 기간별 이력은
 * `GET /assets/{id}/telemetry`(7단계 재생 화면)로 그때그때 조회한다.
 */

export type ConnectionStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

interface OperationsState {
  assetsById: Record<string, TelemetryFrame>;
  alertsById: Record<number, Alert>;
  connectionStatus: ConnectionStatus;
  /** 가장 최근 "재연결"(최초 연결이 아니라 끊겼다가 다시 붙은) 시각. `ResyncBanner`가 쓴다. */
  lastReconnectedAt: number | null;
  selectedAssetId: string | null;

  applySnapshot: (assets: TelemetryFrame[], alerts: Alert[]) => void;
  applyUpdate: (asset: TelemetryFrame) => void;
  applyAlert: (alert: Alert) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  markReconnected: () => void;
  selectAsset: (assetId: string | null) => void;
}

export const useOperationsStore = create<OperationsState>((set) => ({
  assetsById: {},
  alertsById: {},
  connectionStatus: "connecting",
  lastReconnectedAt: null,
  selectedAssetId: null,

  applySnapshot: (assets, alerts) =>
    set(() => ({
      assetsById: Object.fromEntries(assets.map((asset) => [asset.asset_id, asset])),
      alertsById: Object.fromEntries(alerts.map((alert) => [alert.id, alert])),
    })),

  applyUpdate: (asset) =>
    set((state) => {
      const previous = state.assetsById[asset.asset_id];
      // WS 메시지는 순서가 뒤섞이지 않는다고 보장되지만(단일 서버 큐), 방어적으로 한 번 더
      // "역순이면 무시" 규칙을 지킨다(백엔드의 asset_latest_state 갱신 정책과 동일 원칙).
      if (previous && Date.parse(previous.event_time) > Date.parse(asset.event_time)) {
        return state;
      }
      return { assetsById: { ...state.assetsById, [asset.asset_id]: asset } };
    }),

  applyAlert: (alert) =>
    set((state) => ({ alertsById: { ...state.alertsById, [alert.id]: alert } })),

  setConnectionStatus: (status) => set({ connectionStatus: status }),
  markReconnected: () => set({ lastReconnectedAt: Date.now() }),
  selectAsset: (assetId) => set({ selectedAssetId: assetId }),
}));
