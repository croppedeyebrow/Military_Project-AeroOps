import type { Feature, FeatureCollection, LineString } from "geojson";

/** 자산별 최근 위치 궤적을 짧게만 유지한다 — 장기 이력을 브라우저에 쌓지 않는다는
 * 원칙(`docs/planning/01_프론트엔드_아키텍처.md`)을 지도의 "실제 이동 경로" 표시에도
 * 적용한 것. 전체 비행 이력 재생은 7단계 `ReplayTimeline`의 몫이다.
 */
export const TRAIL_MAX_POINTS = 50;

export type TrailsByAsset = Map<string, [number, number][]>;

export function appendTrailPoint(
  trails: TrailsByAsset,
  assetId: string,
  lon: number,
  lat: number
): void {
  const points = trails.get(assetId) ?? [];
  const last = points[points.length - 1];
  if (last && last[0] === lon && last[1] === lat) return; // 좌표 변화 없으면 추가 안 함

  points.push([lon, lat]);
  if (points.length > TRAIL_MAX_POINTS) {
    points.splice(0, points.length - TRAIL_MAX_POINTS);
  }
  trails.set(assetId, points);
}

export function buildTrailsGeoJSON(trails: TrailsByAsset): FeatureCollection<LineString> {
  const features: Feature<LineString>[] = [];
  for (const [assetId, points] of trails) {
    if (points.length < 2) continue;
    features.push({
      type: "Feature",
      properties: { asset_id: assetId },
      geometry: { type: "LineString", coordinates: points },
    });
  }
  return { type: "FeatureCollection", features };
}
