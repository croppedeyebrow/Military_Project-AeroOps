import { describe, expect, it } from "vitest";
import type { Geofence, MissionRoute } from "../../types/mission";
import { buildGeofencesGeoJSON, buildMissionRoutesGeoJSON } from "./layers";

describe("buildMissionRoutesGeoJSON", () => {
  it("converts routes to LineString features, dropping altitude", () => {
    const routes: MissionRoute[] = [
      {
        mission_id: "m1",
        waypoints: [
          [127.0, 37.5, 100],
          [127.01, 37.51, 120],
        ],
        recorded_at: "2026-01-01T00:00:00Z",
      },
    ];
    const geojson = buildMissionRoutesGeoJSON(routes);
    expect(geojson.features).toHaveLength(1);
    expect(geojson.features[0].geometry.coordinates).toEqual([
      [127.0, 37.5],
      [127.01, 37.51],
    ]);
    expect(geojson.features[0].properties?.mission_id).toBe("m1");
  });
});

describe("buildGeofencesGeoJSON", () => {
  it("attaches a fillColor per zone_type for data-driven styling", () => {
    const geofences: Geofence[] = [
      {
        id: "gf-1",
        name: "금지구역",
        zone_type: "PROHIBITED",
        polygon: [
          [126.99, 37.49],
          [127.01, 37.49],
          [127.01, 37.51],
          [126.99, 37.51],
          [126.99, 37.49],
        ],
        created_at: "2026-01-01T00:00:00Z",
      },
    ];
    const geojson = buildGeofencesGeoJSON(geofences);
    expect(geojson.features[0].properties?.fillColor).toBe("#dc143c");
    expect(geojson.features[0].geometry.coordinates[0]).toHaveLength(5);
  });

  it("falls back to a default color for an unknown zone type", () => {
    const geofences = [
      { id: "gf-2", name: "?", zone_type: "WEIRD", polygon: [[0, 0], [1, 0], [1, 1], [0, 0]], created_at: "" },
    ] as unknown as Geofence[];
    const geojson = buildGeofencesGeoJSON(geofences);
    expect(geojson.features[0].properties?.fillColor).toBe("#888888");
  });
});
