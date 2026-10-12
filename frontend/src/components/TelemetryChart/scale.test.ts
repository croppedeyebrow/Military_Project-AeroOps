import { describe, expect, it } from "vitest";
import { buildLinePath, extentWithPadding, scaleLinear } from "./scale";

describe("scaleLinear", () => {
  it("maps the domain minimum to 0", () => {
    expect(scaleLinear(0, { min: 0, max: 100 }, 200)).toBe(0);
  });

  it("maps the domain maximum to rangePx", () => {
    expect(scaleLinear(100, { min: 0, max: 100 }, 200)).toBe(200);
  });

  it("maps the domain midpoint to half the range", () => {
    expect(scaleLinear(50, { min: 0, max: 100 }, 200)).toBe(100);
  });

  it("returns the midpoint when the domain has zero width (no divide-by-zero)", () => {
    expect(scaleLinear(42, { min: 42, max: 42 }, 200)).toBe(100);
  });
});

describe("extentWithPadding", () => {
  it("pads 10% above and below the min/max", () => {
    const extent = extentWithPadding([0, 100]);
    expect(extent.min).toBe(-10);
    expect(extent.max).toBe(110);
  });

  it("uses a fixed fallback padding when every value is identical", () => {
    const extent = extentWithPadding([50, 50, 50], 5);
    expect(extent).toEqual({ min: 45, max: 55 });
  });

  it("returns a default extent for an empty list", () => {
    expect(extentWithPadding([])).toEqual({ min: 0, max: 1 });
  });
});

describe("buildLinePath", () => {
  const timeDomain = { min: 0, max: 100 };
  const valueDomain = { min: 0, max: 100 };

  it("returns an empty string for no points", () => {
    expect(buildLinePath([], timeDomain, valueDomain, 200, 100)).toBe("");
  });

  it("starts with M and uses L for subsequent points", () => {
    const path = buildLinePath(
      [
        { timeMs: 0, value: 0 },
        { timeMs: 100, value: 100 },
      ],
      timeDomain,
      valueDomain,
      200,
      100
    );
    expect(path.startsWith("M")).toBe(true);
    expect(path).toContain("L");
  });

  it("flips the y axis so a larger value is drawn higher (smaller y)", () => {
    const path = buildLinePath(
      [
        { timeMs: 0, value: 0 }, // bottom
        { timeMs: 100, value: 100 }, // top
      ],
      timeDomain,
      valueDomain,
      200,
      100
    );
    const [firstPoint, secondPoint] = path.match(/[ML][\d.]+,[\d.]+/g)!;
    const firstY = Number(firstPoint.split(",")[1]);
    const secondY = Number(secondPoint.split(",")[1]);
    expect(secondY).toBeLessThan(firstY);
  });
});
