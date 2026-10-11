import { beforeEach, describe, expect, it } from "vitest";
import { useReplayStore } from "./useReplayStore";

beforeEach(() => {
  useReplayStore.setState({
    selectedSessionId: null,
    rangeStartMs: null,
    rangeEndMs: null,
    currentTimeMs: null,
    isPlaying: false,
    speed: 1,
  });
});

describe("useReplayStore", () => {
  it("selectSession sets the range and resets the cursor to the start, paused", () => {
    useReplayStore.getState().selectSession("session-1", 1_000, 5_000);
    const state = useReplayStore.getState();
    expect(state.selectedSessionId).toBe("session-1");
    expect(state.rangeStartMs).toBe(1_000);
    expect(state.rangeEndMs).toBe(5_000);
    expect(state.currentTimeMs).toBe(1_000);
    expect(state.isPlaying).toBe(false);
  });

  it("play sets isPlaying", () => {
    useReplayStore.getState().selectSession("session-1", 0, 10_000);
    useReplayStore.getState().play();
    expect(useReplayStore.getState().isPlaying).toBe(true);
  });

  it("play restarts from the beginning when already at the end", () => {
    useReplayStore.getState().selectSession("session-1", 0, 10_000);
    useReplayStore.getState().seek(10_000);
    useReplayStore.getState().play();
    const state = useReplayStore.getState();
    expect(state.currentTimeMs).toBe(0);
    expect(state.isPlaying).toBe(true);
  });

  it("pause clears isPlaying", () => {
    useReplayStore.getState().selectSession("session-1", 0, 10_000);
    useReplayStore.getState().play();
    useReplayStore.getState().pause();
    expect(useReplayStore.getState().isPlaying).toBe(false);
  });

  it("seek clamps to the selected range", () => {
    useReplayStore.getState().selectSession("session-1", 1_000, 5_000);
    useReplayStore.getState().seek(-500);
    expect(useReplayStore.getState().currentTimeMs).toBe(1_000);
    useReplayStore.getState().seek(9_000);
    expect(useReplayStore.getState().currentTimeMs).toBe(5_000);
  });

  it("seek without a selected session is a no-op", () => {
    useReplayStore.getState().seek(123);
    expect(useReplayStore.getState().currentTimeMs).toBeNull();
  });

  it("tick advances currentTimeMs by elapsed*speed while playing", () => {
    useReplayStore.getState().selectSession("session-1", 0, 10_000);
    useReplayStore.getState().setSpeed(2);
    useReplayStore.getState().play();
    useReplayStore.getState().tick(1_000);
    expect(useReplayStore.getState().currentTimeMs).toBe(2_000);
  });

  it("tick does nothing while paused", () => {
    useReplayStore.getState().selectSession("session-1", 0, 10_000);
    useReplayStore.getState().tick(1_000);
    expect(useReplayStore.getState().currentTimeMs).toBe(0);
  });

  it("tick auto-pauses when it reaches the end of the range", () => {
    useReplayStore.getState().selectSession("session-1", 0, 1_000);
    useReplayStore.getState().play();
    useReplayStore.getState().tick(5_000);
    const state = useReplayStore.getState();
    expect(state.currentTimeMs).toBe(1_000);
    expect(state.isPlaying).toBe(false);
  });
});
