import { describe, expect, it } from "vitest";
import { formatElapsed } from "./format";

describe("formatElapsed", () => {
  it("formats seconds", () => {
    expect(formatElapsed(5_000)).toBe("5초 전");
  });

  it("formats minutes", () => {
    expect(formatElapsed(125_000)).toBe("2분 전");
  });

  it("formats hours", () => {
    expect(formatElapsed(3 * 60 * 60 * 1000)).toBe("3시간 전");
  });

  it("treats negative elapsed as just now (clock skew guard)", () => {
    expect(formatElapsed(-500)).toBe("방금 전");
  });
});
