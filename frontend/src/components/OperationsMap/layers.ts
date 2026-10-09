import type { Feature, FeatureCollection, LineString, Polygon } from "geojson";
import type { Geofence, MissionRoute } from "../../types/mission";

/** 예정 경로(점선)용 GeoJSON. */
export function buildMissionRoutesGeoJSON(routes: MissionRoute[]): FeatureCollection<LineString> {
  const features: Feature<LineString>[] = routes.map((route) => ({
    type: "Feature",
    properties: { mission_id: route.mission_id },
    geometry: {
      type: "LineString",
      coordinates: route.waypoints.map(([lon, lat]) => [lon, lat]),
    },
  }));
  return { type: "FeatureCollection", features };
}

const ZONE_FILL_COLOR: Record<string, string> = {
  MISSION: "#3388ff",
  CAUTION: "#daa520",
  PROHIBITED: "#dc143c",
};

/** 구역(임무·주의·금지) 폴리곤용 GeoJSON. `fillColor` feature 속성은 data-driven 스타일에 쓴다. */
export function buildGeofencesGeoJSON(geofences: Geofence[]): FeatureCollection<Polygon> {
  const features: Feature<Polygon>[] = geofences.map((geofence) => ({
    type: "Feature",
    properties: {
      geofence_id: geofence.id,
      name: geofence.name,
      zone_type: geofence.zone_type,
      fillColor: ZONE_FILL_COLOR[geofence.zone_type] ?? "#888888",
    },
    geometry: { type: "Polygon", coordinates: [geofence.polygon] },
  }));
  return { type: "FeatureCollection", features };
}
