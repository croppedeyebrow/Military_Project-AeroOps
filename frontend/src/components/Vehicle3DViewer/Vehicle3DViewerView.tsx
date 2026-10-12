import { useEffect, useRef } from "react";
import * as THREE from "three";
import { theme } from "../../styles/theme";
import type { AssetFreshness, TelemetryFrame } from "../../types/telemetry";
import { quaternionFromAttitude } from "./attitude";
import { buildDroneMesh, disposeDroneMesh } from "./buildDroneMesh";
import { buildDirectionGuides } from "./guides";

interface SceneContext {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  droneGroup: THREE.Group | null;
  guides: ReturnType<typeof buildDirectionGuides> | null;
}

export interface Vehicle3DViewerViewProps {
  selectedAssetId: string | null;
  asset: TelemetryFrame | undefined;
  /** `null`이면 "오래된 자세값일 수 있음" 배지를 숨긴다(신선도 개념이 없는 컨텍스트 —
   * 재생 화면처럼 "지금 몇 시냐"가 없는 곳에선 호출부가 그냥 `null`을 넘긴다). */
  freshness: AssetFreshness | null;
  /** `undefined`면 "최근 연관 명령" 줄 자체를 그리지 않는다(이 기능이 의미 없는
   * 컨텍스트 — 재생 화면은 아직 명령 이력을 재생 시각 기준으로 보여주지 않는다,
   * `ReplayVehicle3DViewer` 참고). `null`이면 "없음"으로 표시한다. */
  recentCommandLabel?: string | null;
}

/**
 * `Vehicle3DViewer`(실시간)와 `ReplayVehicle3DViewer`(재생)가 공유하는 실제 렌더링
 * 로직. 데이터를 어디서 가져오는지(실시간 store vs 재생 데이터셋)는 이 컴포넌트가
 * 전혀 모른다 — props로만 받는다. 좌표축·회전 부호 규칙은
 * [`docs/decisions/0003-vehicle-3d-axis-convention.md`](../../../../docs/decisions/0003-vehicle-3d-axis-convention.md).
 *
 * three.js 렌더러/씬/카메라는 컴포넌트 수명 동안 한 번만 만들고, 기체 선택이 바뀔 때만
 * drone 메시(+보조선)를 새로 만들어 교체한다. 자세 갱신(실시간 ~1Hz 또는 재생 스크럽)마다
 * requestAnimationFrame 루프를 돌리지 않고, `asset`이 바뀔 때만 쿼터니언을 갱신하고
 * 1프레임 렌더한다 — 두 호출부 모두 이미 자기 쪽에서 적절한 빈도로만 `asset`을 갱신해
 * 넘겨준다(실시간은 WS 수신 시, 재생은 재생 시계 tick 시).
 */
export function Vehicle3DViewerView({
  selectedAssetId,
  asset,
  freshness,
  recentCommandLabel,
}: Vehicle3DViewerViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const ctxRef = useRef<SceneContext | null>(null);

  // 렌더러/씬/카메라: 마운트 시 1회 생성, 언마운트 시 전체 해제.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth || 1;
    const height = container.clientHeight || 1;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // 버그 수정(2026-10-12, 스크린샷으로 발견): 다크 테마 전환 전 배경(#f2f2f2, 밝은
    // 회색)이 그대로 남아있어 주변 패널과 확연히 떠 보였다. 그리드도 같이 어둡게
    // 맞춘다 — theme.color.background.sunken과 같은 "패널보다 가라앉은 영역" 색을 써서
    // OperationsMapView의 지도 캔버스 기본 배경과 톤을 맞췄다.
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(theme.color.background.sunken);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 100);
    camera.position.set(1.1, 0.85, 1.1);
    camera.lookAt(0, 0, 0);

    // 조명은 흰색·세기 그대로 유지한다(조명 자체의 색은 배경과 무관 — 재질에 반사돼
    // 보이는 색이 중요하다). 그리드 선만 어두운 배경에서 은은하게 보이는 톤으로 낮췄다.
    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.7);
    dirLight.position.set(2, 3, 1.5);
    scene.add(dirLight);
    scene.add(new THREE.GridHelper(1.6, 8, theme.color.border.default, theme.color.border.subtle));

    ctxRef.current = { renderer, scene, camera, droneGroup: null, guides: null };
    renderer.render(scene, camera);

    return () => {
      const ctx = ctxRef.current;
      if (ctx) {
        if (ctx.droneGroup) disposeDroneMesh(ctx.droneGroup);
        ctx.guides?.dispose();
        ctx.renderer.dispose();
      }
      container.removeChild(renderer.domElement);
      ctxRef.current = null;
    };
  }, []);

  // 기체 선택 변경: 이전 메시 dispose 후 새 메시(+보조선) 교체.
  useEffect(() => {
    const ctx = ctxRef.current;
    if (!ctx) return;

    if (ctx.droneGroup) {
      ctx.scene.remove(ctx.droneGroup);
      disposeDroneMesh(ctx.droneGroup);
      ctx.droneGroup = null;
    }
    if (ctx.guides) {
      ctx.scene.remove(ctx.guides.group);
      ctx.guides.dispose();
      ctx.guides = null;
    }

    if (selectedAssetId) {
      const droneGroup = buildDroneMesh();
      const guides = buildDirectionGuides();
      ctx.scene.add(droneGroup, guides.group);
      ctx.droneGroup = droneGroup;
      ctx.guides = guides;
    }

    ctx.renderer.render(ctx.scene, ctx.camera);
  }, [selectedAssetId]);

  // 자세 갱신: 쿼터니언만 갱신하고 1프레임 렌더.
  useEffect(() => {
    const ctx = ctxRef.current;
    if (!ctx || !ctx.droneGroup || !ctx.guides || !asset) return;

    const attitude = {
      headingDeg: asset.heading_deg ?? asset.yaw_deg ?? 0,
      rollDeg: asset.roll_deg ?? 0,
      pitchDeg: asset.pitch_deg ?? 0,
    };
    ctx.droneGroup.quaternion.copy(quaternionFromAttitude(attitude));
    ctx.guides.update(attitude);
    ctx.renderer.render(ctx.scene, ctx.camera);
  }, [asset]);

  if (!selectedAssetId) {
    return (
      <div style={{ padding: "0.75rem", color: "gray", fontSize: "0.9em" }}>
        지도 또는 목록에서 기체를 선택하면 3D 자세를 표시합니다.
      </div>
    );
  }

  return (
    <div>
      <div
        ref={containerRef}
        style={{ width: "100%", height: 200, position: "relative" }}
        data-testid="vehicle-3d-canvas-container"
      />
      {freshness && freshness !== "live" && (
        <div style={{ padding: "0.25rem 0.75rem", color: "#a36b00", fontSize: "0.8em" }}>
          {freshness === "stale" ? "신호 약함 — 자세값이 오래됐을 수 있습니다." : "통신 단절 — 마지막 수신 자세값입니다."}
        </div>
      )}
      {recentCommandLabel !== undefined && (
        <div style={{ padding: "0.25rem 0.75rem", color: "gray", fontSize: "0.8em" }}>
          {recentCommandLabel ?? "최근 연관 명령 없음"}
        </div>
      )}
    </div>
  );
}
