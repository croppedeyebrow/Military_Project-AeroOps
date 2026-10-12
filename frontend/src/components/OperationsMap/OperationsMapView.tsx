import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import { theme } from "../../styles/theme";
import type { Geofence, MissionRoute } from "../../types/mission";
import type { TelemetryFrame } from "../../types/telemetry";
import { buildGeofencesGeoJSON, buildMissionRoutesGeoJSON } from "./layers";
import { createHqMarkerElement, createMarkerElement, updateMarkerElement } from "./markerElement";
import { appendTrailPoint, buildTrailsGeoJSON, type TrailsByAsset } from "./trails";

/**
 * 지도 스타일. 사용자 결정(2026-10-12, 스크린샷으로 발견한 문제의 후속): 원래 쓰던
 * `demotiles.maplibre.org`(MapLibre 공식 데모 벡터 스타일)는 실제 타일 데이터가 거의
 * 없어서 — 특히 서울처럼 유럽/미국 외 지역은 — 빈 배경색만 보이는 문제가 있었다.
 * API 키 없는 OpenStreetMap 표준 래스터 타일로 바꾼다 — 전 세계 실제 지도가 보인다.
 * `VITE_MAP_STYLE_URL`을 설정하면(예: 실제 배포 시 유료 벡터 타일 서비스) 이 기본값
 * 대신 그 URL을 그대로 스타일로 쓴다.
 *
 * OSM 표준 타일은 밝은(흰색 위주) 스타일이라 다크 테마와 안 어울린다 — 아래 "load"
 * 핸들러에서 레이어 자체가 아니라 raster paint 속성(brightness/contrast/saturation)
 * 으로만 어둡게 보정한다. 캔버스 전체에 CSS `filter`를 거는 방법도 있지만, 그러면
 * 같은 캔버스에 그리는 우리 자체 레이어(트레일·경로·구역)의 색까지 같이 뒤틀린다 —
 * raster paint는 이 레이어 하나에만 적용돼 그 문제가 없다.
 */
const OSM_RASTER_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    "osm-raster": {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm-raster-layer", type: "raster", source: "osm-raster" }],
};
const MAP_STYLE = import.meta.env.VITE_MAP_STYLE_URL || OSM_RASTER_STYLE;
const TRAILS_SOURCE_ID = "asset-trails";
const TRAILS_LAYER_ID = "asset-trails-line";
const ROUTES_SOURCE_ID = "mission-routes";
const ROUTES_LAYER_ID = "mission-routes-line";
const GEOFENCES_SOURCE_ID = "geofences";
const GEOFENCES_FILL_LAYER_ID = "geofences-fill";
const GEOFENCES_OUTLINE_LAYER_ID = "geofences-outline";
// 사용자 결정(2026-10-12): 편대 출발지를 성남 판교로 — 판교테크노밸리역 인근 좌표.
// `simulator/simulator/generator.py`의 `BASE_LAT`/`BASE_LON`과 반드시 같은 값을
// 유지해야 한다("본부에서 출발했다"는 그림이 두 쪽에서 어긋나면 안 된다).
const BASE_ORIGIN: [number, number] = [127.1112, 37.3947];
const DEFAULT_CENTER = BASE_ORIGIN;

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
  const hqMarkerRef = useRef<maplibregl.Marker | null>(null);

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
      style: MAP_STYLE,
      center: DEFAULT_CENTER,
      zoom: 12,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapRef.current = map;

    map.on("load", () => {
      // OSM 래스터 타일 보정(이 레이어에만 적용 — 위 OSM_RASTER_STYLE 주석 참고).
      // VITE_MAP_STYLE_URL로 다른 스타일을 쓸 땐 이 레이어가 없으니 조용히 건너뛴다.
      //
      // 사용자 결정(2026-10-12): 실제 좌표(판교)는 그대로 쓰되 "전술 지도" 느낌을
      // 입힌다. `raster-hue-rotate`로 OSM 특유의 녹색/회색 팔레트를 올리브·카키 쪽으로
      // 돌리고, 대비를 더 올려 등고선·격자 느낌을 강조한다 — 실제 타일 이미지 자체를
      // 새로 만드는 게 아니라 이미 받은 이미지에 색 보정만 거는 것이라 새 타일
      // 서버·의존성이 필요 없다.
      if (map.getLayer("osm-raster-layer")) {
        map.setPaintProperty("osm-raster-layer", "raster-brightness-max", 0.55);
        map.setPaintProperty("osm-raster-layer", "raster-contrast", 0.3);
        map.setPaintProperty("osm-raster-layer", "raster-saturation", -0.3);
        map.setPaintProperty("osm-raster-layer", "raster-hue-rotate", 45);
      }

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
        // 어두워진 타일 위에서도 구분되게 밝은 회색으로(기존 #666666은 어두운 타일
        // 배경과 거의 묻혀 보인다).
        paint: { "line-color": theme.color.text.secondary, "line-width": 2, "line-dasharray": [2, 2] },
      });

      map.addSource(TRAILS_SOURCE_ID, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: TRAILS_LAYER_ID,
        type: "line",
        source: TRAILS_SOURCE_ID,
        // theme.color.accent(네온 시안)로 통일 — 기존 #3388ff는 다크 테마 전환 전 accent.
        paint: { "line-color": theme.color.accent, "line-width": 2, "line-opacity": 0.8 },
      });

      // 본부(HQ) 마커 — 기체 마커(위 TRAILS 루프)와 달리 데이터가 바뀌어도 움직이지
      // 않는 고정 지형지물이라 여기(마운트 시 1회)에서만 만든다.
      hqMarkerRef.current = new maplibregl.Marker({ element: createHqMarkerElement() })
        .setLngLat(BASE_ORIGIN)
        .addTo(map);

      mapLoadedRef.current = true;
    });

    return () => {
      map.remove();
      mapRef.current = null;
      mapLoadedRef.current = false;
      markersRef.current.clear();
      trailsRef.current.clear();
      hqMarkerRef.current = null;
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

  return (
    <div
      ref={containerRef}
      // 버그 수정(2026-10-12, 스크린샷으로 발견): 배경색이 없으면 지도 캔버스가 아직
      // 로드되지 않았거나(또는 데모 스타일이 그 지역 타일 데이터가 없어 빈 영역일 때)
      // 뒤에 아무것도 없어 OS 바탕화면이 비쳐 보였다. 타일 로딩 성공 여부와 무관하게
      // 항상 테마 배경색이 먼저 깔리게 한다 — MapLibre가 그 위에 실제 타일을 그린다.
      style={{ width: "100%", height: "100%", background: theme.color.background.sunken }}
    />
  );
}
