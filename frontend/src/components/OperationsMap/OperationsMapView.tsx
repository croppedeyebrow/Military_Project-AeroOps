import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import type { Geofence, MissionRoute } from "../../types/mission";
import type { TelemetryFrame } from "../../types/telemetry";
import { buildGeofencesGeoJSON, buildMissionRoutesGeoJSON } from "./layers";
import { createMarkerElement, updateMarkerElement } from "./markerElement";
import { appendTrailPoint, buildTrailsGeoJSON, type TrailsByAsset } from "./trails";

// 별도 API 키가 필요 없는 공개 데모 스타일. 실제 배포 시 VITE_MAP_STYLE_URL로 바꾼다.
const MAP_STYLE_URL =
  import.meta.env.VITE_MAP_STYLE_URL || "https://demotiles.maplibre.org/style.json";
const TRAILS_SOURCE_ID = "asset-trails";
const TRAILS_LAYER_ID = "asset-trails-line";
const ROUTES_SOURCE_ID = "mission-routes";
const ROUTES_LAYER_ID = "mission-routes-line";
const GEOFENCES_SOURCE_ID = "geofences";
const GEOFENCES_FILL_LAYER_ID = "geofences-fill";
const GEOFENCES_OUTLINE_LAYER_ID = "geofences-outline";
const DEFAULT_CENTER: [number, number] = [127.0, 37.5];

export interface OperationsMapViewProps {
  assetsById: Record<string, TelemetryFrame>;
  selectedAssetId: string | null;
  onSelectAsset: (assetId: string) => void;
  /** 재생 화면은 지금(Unit 3 범위에서는) 임무 경로·구역을 보여주지 않는다 — 생략하면
   * 빈 레이어로 그려진다. */
  missionRoutes?: MissionRoute[];
  geofences?: Geofence[];
}

/**
 * `OperationsMap`(실시간)과 `ReplayMap`(재생)이 공유하는 실제 MapLibre 렌더링 로직.
 * 데이터를 어디서 가져오는지는 이 컴포넌트가 모른다 — props로만 받는다(사용자 결정
 * 2026-10-11: 재생은 실시간 화면과 분리된 별도 탭이지만, 렌더링 로직 자체는 중복
 * 작성하지 않는다).
 *
 * 마커·궤적·레이어 그리기는 이미 순수 함수로 분리돼 있다(`markerElement.ts`/
 * `layers.ts`/`trails.ts`) — 이 컴포넌트는 그 함수들을 MapLibre 생명주기에 맞춰
 * 호출하는 역할만 한다.
 */
export function OperationsMapView({
  assetsById,
  selectedAssetId,
  onSelectAsset,
  missionRoutes,
  geofences,
}: OperationsMapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const mapLoadedRef = useRef(false);
  const markersRef = useRef<Map<string, maplibregl.Marker>>(new Map());
  const trailsRef = useRef<TrailsByAsset>(new Map());

  // "load" 이벤트 핸들러는 마운트 시 한 번만 만들어지지만, 실제 발생 시점엔 이 ref들을
  // 통해 그 순간의 최신 props를 읽는다(props가 지도 로드보다 먼저 도착했을 수도 있다).
  const missionRoutesRef = useRef(missionRoutes);
  const geofencesRef = useRef(geofences);
  missionRoutesRef.current = missionRoutes;
  geofencesRef.current = geofences;

  // 지도 인스턴스는 마운트 시 한 번만 만든다.
  useEffect(() => {
    if (!containerRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE_URL,
      center: DEFAULT_CENTER,
      zoom: 12,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current = map;

    map.on("load", () => {
      // 구역 폴리곤을 가장 아래에(다른 레이어에 가려지지 않게), 그 위에 예정 경로,
      // 그 위에 실제 이동 궤적 순서로 쌓는다.
      map.addSource(GEOFENCES_SOURCE_ID, {
        type: "geojson",
        data: buildGeofencesGeoJSON(geofencesRef.current ?? []),
      });
      map.addLayer({
        id: GEOFENCES_FILL_LAYER_ID,
        type: "fill",
        source: GEOFENCES_SOURCE_ID,
        paint: { "fill-color": ["get", "fillColor"], "fill-opacity": 0.15 },
      });
      map.addLayer({
        id: GEOFENCES_OUTLINE_LAYER_ID,
        type: "line",
        source: GEOFENCES_SOURCE_ID,
        paint: { "line-color": ["get", "fillColor"], "line-width": 1.5 },
      });

      map.addSource(ROUTES_SOURCE_ID, {
        type: "geojson",
        data: buildMissionRoutesGeoJSON(missionRoutesRef.current ?? []),
      });
      map.addLayer({
        id: ROUTES_LAYER_ID,
        type: "line",
        source: ROUTES_SOURCE_ID,
        paint: { "line-color": "#666666", "line-width": 2, "line-dasharray": [2, 2] },
      });

      map.addSource(TRAILS_SOURCE_ID, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: TRAILS_LAYER_ID,
        type: "line",
        source: TRAILS_SOURCE_ID,
        paint: { "line-color": "#3388ff", "line-width": 2, "line-opacity": 0.7 },
      });
      mapLoadedRef.current = true;
    });

    return () => {
      map.remove();
      mapRef.current = null;
      mapLoadedRef.current = false;
      markersRef.current.clear();
      trailsRef.current.clear();
    };
  }, []);

  // 자산 상태가 바뀔 때마다 마커·궤적을 갱신한다.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const seenIds = new Set(Object.keys(assetsById));
    for (const [assetId, marker] of markersRef.current) {
      if (!seenIds.has(assetId)) {
        marker.remove();
        markersRef.current.delete(assetId);
        trailsRef.current.delete(assetId);
      }
    }

    const now = Date.now();
    for (const asset of Object.values(assetsById)) {
      let marker = markersRef.current.get(asset.asset_id);
      if (!marker) {
        const el = createMarkerElement();
        el.addEventListener("click", (event) => {
          event.stopPropagation();
          onSelectAsset(asset.asset_id);
        });
        marker = new maplibregl.Marker({ element: el })
          .setLngLat([asset.longitude, asset.latitude])
          .addTo(map);
        markersRef.current.set(asset.asset_id, marker);
      } else {
        marker.setLngLat([asset.longitude, asset.latitude]);
      }
      updateMarkerElement(
        marker.getElement() as HTMLDivElement,
        asset,
        asset.asset_id === selectedAssetId,
        now
      );
      appendTrailPoint(trailsRef.current, asset.asset_id, asset.longitude, asset.latitude);
    }

    if (mapLoadedRef.current) {
      const source = map.getSource(TRAILS_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
      source?.setData(buildTrailsGeoJSON(trailsRef.current));
    }
  }, [assetsById, selectedAssetId, onSelectAsset]);

  // 예정 경로(점선) — 진행 중인 임무 목록/경로가 바뀔 때마다 갱신한다.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoadedRef.current) return;
    const source = map.getSource(ROUTES_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    source?.setData(buildMissionRoutesGeoJSON(missionRoutes ?? []));
  }, [missionRoutes]);

  // 구역 폴리곤 — 목록이 바뀔 때마다 갱신한다.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoadedRef.current) return;
    const source = map.getSource(GEOFENCES_SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    source?.setData(buildGeofencesGeoJSON(geofences ?? []));
  }, [geofences]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
