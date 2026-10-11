import { describe, expect, it } from "vitest";
import { advanceReplayTime } from "./replayClock";

describe("advanceReplayTime", () => {
  it("1배속이면 실시간 경과만큼 그대로 전진한다", () => {
    const result = advanceReplayTime(1_000, 500, 1, 10_000);
    expect(result).toEqual({ nextTimeMs: 1_500, finished: false });
  });

  it("2배속이면 실시간 경과의 2배만큼 전진한다", () => {
    const result = advanceReplayTime(1_000, 500, 2, 10_000);
    expect(result.nextTimeMs).toBe(2_000);
  });

  it("0.5배속이면 실시간 경과의 절반만큼 전진한다", () => {
    const result = advanceReplayTime(1_000, 500, 0.5, 10_000);
    expect(result.nextTimeMs).toBe(1_250);
  });

  it("구간 끝에 도달하면 끝 시각으로 고정하고 finished=true", () => {
    const result = advanceReplayTime(9_800, 500, 1, 10_000);
    expect(result).toEqual({ nextTimeMs: 10_000, finished: true });
  });

  it("구간 끝을 정확히 넘지 않으면 finished=false", () => {
    const result = advanceReplayTime(9_000, 500, 1, 10_000);
    expect(result.finished).toBe(false);
  });
});
