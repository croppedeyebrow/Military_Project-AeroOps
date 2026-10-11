import { create } from "zustand";
import { advanceReplayTime } from "./replayClock";

/**
 * 재생 탭 전용 상태(Zustand) — 실시간 관제의 `useOperationsStore`와 완전히 분리한다.
 *
 * 근거: 사용자 결정(2026-10-11) — 재생은 지도·3D를 실시간 화면과 공유하지 않고 별도
 * 탭/화면으로 둔다. 그래서 "지금 재생 중인 시각이 몇 시인지", "어느 세션을 재생하는지"
 * 같은 상태도 실시간 store와 섞을 이유가 없다 — 완전히 별개의 화면이 쓰는 별개의 상태다.
 *
 * `docs/planning/01_프론트엔드_아키텍처.md` "재생 Controller"에 대응한다.
 */
export type ReplaySpeed = 0.5 | 1 | 2;

interface ReplayState {
  selectedSessionId: string | null;
  /** 재생 구간의 시작/끝(ms, epoch) — 세션을 고르면 세션의 started_at/ended_at으로
   * 채워진다. 세션 선택 전에는 재생할 구간 자체가 없으므로 null. */
  rangeStartMs: number | null;
  rangeEndMs: number | null;
  currentTimeMs: number | null;
  isPlaying: boolean;
  speed: ReplaySpeed;
  /** 재생 화면에서 지도/목록으로 고른 기체 — `useOperationsStore.selectedAssetId`와
   * 같은 역할이지만 재생 화면 전용으로 분리한다(화면 자체가 분리돼 있으므로). */
  selectedAssetId: string | null;

  selectSession: (sessionId: string, rangeStartMs: number, rangeEndMs: number) => void;
  play: () => void;
  pause: () => void;
  seek: (timeMs: number) => void;
  setSpeed: (speed: ReplaySpeed) => void;
  selectAsset: (assetId: string | null) => void;
  /** `requestAnimationFrame` 루프(컴포넌트 쪽)가 매 프레임 실제 경과 시간을 넘긴다.
   * 구간 끝에 닿으면 스스로 멈춘다(`advanceReplayTime`의 `finished`). */
  tick: (elapsedRealMs: number) => void;
}

export const useReplayStore = create<ReplayState>((set, get) => ({
  selectedSessionId: null,
  rangeStartMs: null,
  rangeEndMs: null,
  currentTimeMs: null,
  isPlaying: false,
  speed: 1,
  selectedAssetId: null,

  selectSession: (sessionId, rangeStartMs, rangeEndMs) =>
    set({
      selectedSessionId: sessionId,
      rangeStartMs,
      rangeEndMs,
      currentTimeMs: rangeStartMs, // 새 세션을 고르면 항상 처음부터 — 이전 세션의 커서
      // 위치를 이어받으면 "지금 뭘 보고 있는지" 헷갈린다.
      isPlaying: false,
      selectedAssetId: null, // 세션이 바뀌면 이전 세션에서 고른 기체 선택도 비운다 —
      // 그 기체가 이번 세션엔 없을 수도 있다.
    }),

  play: () => {
    const { rangeEndMs, currentTimeMs } = get();
    // 구간 끝(또는 그 이후)에서 재생을 누르면 처음으로 되돌아가 다시 시작한다 —
    // "끝에 멈춰있는데 재생을 눌러도 아무 반응이 없다"는 혼란스러운 UX를 막는다.
    if (rangeEndMs !== null && currentTimeMs !== null && currentTimeMs >= rangeEndMs) {
      set({ currentTimeMs: get().rangeStartMs, isPlaying: true });
      return;
    }
    set({ isPlaying: true });
  },

  pause: () => set({ isPlaying: false }),

  seek: (timeMs) => {
    const { rangeStartMs, rangeEndMs } = get();
    if (rangeStartMs === null || rangeEndMs === null) return;
    const clamped = Math.min(Math.max(timeMs, rangeStartMs), rangeEndMs);
    set({ currentTimeMs: clamped });
  },

  setSpeed: (speed) => set({ speed }),

  selectAsset: (assetId) => set({ selectedAssetId: assetId }),

  tick: (elapsedRealMs) => {
    const { isPlaying, currentTimeMs, rangeEndMs, speed } = get();
    if (!isPlaying || currentTimeMs === null || rangeEndMs === null) return;
    const { nextTimeMs, finished } = advanceReplayTime(
      currentTimeMs,
      elapsedRealMs,
      speed,
      rangeEndMs
    );
    set({ currentTimeMs: nextTimeMs, isPlaying: finished ? false : isPlaying });
  },
}));
