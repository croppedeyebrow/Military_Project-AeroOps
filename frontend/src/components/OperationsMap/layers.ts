import type { Feature, FeatureCollection, LineString, Polygon } from "geojson";
import { theme } from "../../styles/theme";
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

// 발견한 5번째 un-wired 색상 맵이었다(2026-10-12 다크 테마 스크린샷 리뷰 중) — 이제
// theme 토큰을 참조한다.
const ZONE_FILL_COLOR: Record<string, string> = {
  MISSION: theme.color.accent,
  CAUTION: theme.color.status.warning,
  PROHIBITED: theme.color.status.danger,
};

/** 구역(임무·주의·금지) 폴리곤용 GeoJSON. `fillColor` feature 속성은 data-driven 스타일에 쓴다. */
export function buildGeofencesGeoJSON(geofences: Geofence[]): FeatureCollection<Polygon> {
  const features: Feature<Polygon>[] = geofences.map((geofence) => ({
    type: "Feature",
    properties: {
      geofence_id: geofence.id,
      name: geofence.name,
      zone_type: geofence.zone_type,
      fillColor: ZONE_FILL_COLOR[geofence.zone_type] ?? theme.color.text.muted,
    },
    geometry: { type: "Polygon", coordinates: [geofence.polygon] },
  }));
  return { type: "FeatureCollection", features };
}
