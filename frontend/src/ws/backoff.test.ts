import { describe, expect, it } from "vitest";
import { computeBackoffDelayMs } from "./backoff";

describe("computeBackoffDelayMs", () => {
  it("returns 0 for the first attempt (no wait before first try)", () => {
    expect(computeBackoffDelayMs(0)).toBe(0);
  });

  it("doubles the delay each attempt", () => {
    expect(computeBackoffDelayMs(1, 1000, 15000)).toBe(1000);
    expect(computeBackoffDelayMs(2, 1000, 15000)).toBe(2000);
    expect(computeBackoffDelayMs(3, 1000, 15000)).toBe(4000);
    expect(computeBackoffDelayMs(4, 1000, 15000)).toBe(8000);
  });

  it("caps at the configured maximum", () => {
    expect(computeBackoffDelayMs(10, 1000, 15000)).toBe(15000);
  });
});
