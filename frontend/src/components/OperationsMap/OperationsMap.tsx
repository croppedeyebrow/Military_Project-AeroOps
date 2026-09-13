import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import { useOperationsStore } from "../../store/useOperationsStore";
import { createMarkerElement, updateMarkerElement } from "./markerElement";
import { appendTrailPoint, buildTrailsGeoJSON, type TrailsByAsset } from "./trails";

// 별도 API 키가 필요 없는 공개 데모 스타일. 실제 배포 시 VITE_MAP_STYLE_URL로 바꾼다.
const MAP_STYLE_URL =
  import.meta.env.VITE_MAP_STYLE_URL || "https://demotiles.maplibre.org/style.json";
const TRAILS_SOURCE_ID = "asset-trails";
const TRAILS_LAYER_ID = "asset-trails-line";
const DEFAULT_CENTER: [number, number] = [127.0, 37.5];

/**
 * MapLibre 기반 2D 관제 지도. 전체 드론 방향 아이콘·호출부호·상태 색상, 실제 이동
 * 경로(실선)를 표시한다(4단계). 예정 경로·구역 폴리곤은 5단계에서 레이어를 추가한다.
 */
export function OperationsMap() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const mapLoadedRef = useRef(false);
  const markersRef = useRef<Map<string, maplibregl.Marker>>(new Map());
  const trailsRef = useRef<TrailsByAsset>(new Map());

  const assetsById = useOperationsStore((s) => s.assetsById);
  const selectedAssetId = useOperationsStore((s) => s.selectedAssetId);
  const selectAsset = useOperationsStore((s) => s.selectAsset);

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
          selectAsset(asset.asset_id);
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
  }, [assetsById, selectedAssetId, selectAsset]);

  return <div ref={containerRef} style={{ width: "100%", height: "100%" }} />;
}
