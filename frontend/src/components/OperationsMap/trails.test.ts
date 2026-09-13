import { describe, expect, it } from "vitest";
import { appendTrailPoint, buildTrailsGeoJSON, TRAIL_MAX_POINTS, type TrailsByAsset } from "./trails";

describe("appendTrailPoint / buildTrailsGeoJSON", () => {
  it("accumulates points per asset", () => {
    const trails: TrailsByAsset = new Map();
    appendTrailPoint(trails, "a", 127.0, 37.5);
    appendTrailPoint(trails, "a", 127.01, 37.51);

    expect(trails.get("a")).toEqual([
      [127.0, 37.5],
      [127.01, 37.51],
    ]);
  });

  it("does not add a duplicate point when the position hasn't changed", () => {
    const trails: TrailsByAsset = new Map();
    appendTrailPoint(trails, "a", 127.0, 37.5);
    appendTrailPoint(trails, "a", 127.0, 37.5);
    expect(trails.get("a")).toHaveLength(1);
  });

  it("caps the trail length at TRAIL_MAX_POINTS", () => {
    const trails: TrailsByAsset = new Map();
    for (let i = 0; i < TRAIL_MAX_POINTS + 10; i++) {
      appendTrailPoint(trails, "a", 127.0 + i * 0.0001, 37.5);
    }
    expect(trails.get("a")).toHaveLength(TRAIL_MAX_POINTS);
    // 가장 오래된 점들이 잘려나가고 최신 점이 남아있어야 한다.
    const last = trails.get("a")!.at(-1)!;
    expect(last[0]).toBeCloseTo(127.0 + (TRAIL_MAX_POINTS + 9) * 0.0001);
  });

  it("builds a LineString feature per asset with 2+ points, skipping single-point trails", () => {
    const trails: TrailsByAsset = new Map([
      ["a", [[127.0, 37.5], [127.01, 37.51]]],
      ["b", [[128.0, 38.0]]], // 점 하나뿐 -> 제외
    ]);
    const geojson = buildTrailsGeoJSON(trails);
    expect(geojson.features).toHaveLength(1);
    expect(geojson.features[0].properties?.asset_id).toBe("a");
  });
});
