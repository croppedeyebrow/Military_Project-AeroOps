import { describe, expect, it } from "vitest";
import type { OperationSession } from "../../types/replay";
import { formatDuration, formatReplayClock, sessionRange } from "./format";

function makeSession(startedAt: string, endedAt: string | null): OperationSession {
  return {
    id: "opsession-test",
    deployment_id: "deploy-test",
    started_at: startedAt,
    ended_at: endedAt,
    started_by: null,
  };
}

describe("sessionRange", () => {
  it("종료된 세션은 started_at~ended_at", () => {
    const range = sessionRange(
      makeSession("2026-01-01T00:00:00Z", "2026-01-01T00:20:00Z"),
      Date.parse("2026-02-01T00:00:00Z")
    );
    expect(range.startMs).toBe(Date.parse("2026-01-01T00:00:00Z"));
    expect(range.endMs).toBe(Date.parse("2026-01-01T00:20:00Z"));
  });

  it("진행 중인 세션(ended_at=null)은 지금(nowMs)을 끝으로 쓴다", () => {
    const now = Date.parse("2026-01-01T00:05:00Z");
    const range = sessionRange(makeSession("2026-01-01T00:00:00Z", null), now);
    expect(range.endMs).toBe(now);
  });

  it("시작과 끝이 같으면 최소 1초 폭을 보장한다", () => {
    const range = sessionRange(
      makeSession("2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z"),
      Date.now()
    );
    expect(range.endMs - range.startMs).toBe(1_000);
  });
});

describe("formatDuration", () => {
  it("1시간 미만은 mm:ss", () => {
    expect(formatDuration(83_000)).toBe("01:23");
  });

  it("1시간 이상은 h:mm:ss", () => {
    expect(formatDuration(3_723_000)).toBe("1:02:03");
  });

  it("음수는 00:00", () => {
    expect(formatDuration(-5_000)).toBe("00:00");
  });
});

describe("formatReplayClock", () => {
  it("경과 / 전체 형태로 보여준다", () => {
    const range = { startMs: 0, endMs: 20 * 60_000 };
    expect(formatReplayClock(83_000, range)).toBe("01:23 / 20:00");
  });
});
