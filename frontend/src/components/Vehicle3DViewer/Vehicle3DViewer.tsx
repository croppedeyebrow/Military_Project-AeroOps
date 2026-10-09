import { useEffect, useRef } from "react";
import * as THREE from "three";
import { useAssetCommandsQuery } from "../../api/commands";
import { useOperationsStore } from "../../store/useOperationsStore";
import { classifyFreshness } from "../../types/telemetry";
import { quaternionFromAttitude } from "./attitude";
import { buildDroneMesh, disposeDroneMesh } from "./buildDroneMesh";
import { buildDirectionGuides } from "./guides";
import { Vehicle3DErrorBoundary } from "./Vehicle3DErrorBoundary";

interface SceneContext {
  renderer: THREE.WebGLRenderer;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  droneGroup: THREE.Group | null;
  guides: ReturnType<typeof buildDirectionGuides> | null;
}

/**
 * 선택 기체만 3D로 표현한다(전체 기체는 2D 지도 — `docs/planning/01_프론트엔드_아키텍처.md`
 * "시각화 규칙"). 좌표축·회전 부호 규칙은
 * [`docs/decisions/0003-vehicle-3d-axis-convention.md`](../../../../docs/decisions/0003-vehicle-3d-axis-convention.md).
 *
 * three.js 렌더러/씬/카메라는 컴포넌트 수명 동안 한 번만 만들고, 기체 선택이 바뀔 때만
 * drone 메시(+보조선)를 새로 만들어 교체한다(geometry/material은 교체 전 `dispose`).
 * 텔레메트리 갱신(~1Hz)마다 requestAnimationFrame 루프를 돌리지 않고, 값이 바뀔 때만
 * 쿼터니언을 갱신하고 1프레임 렌더한다 — WebSocket 수신 빈도와 맞아 불필요한 GPU 작업이 없다.
 */
function Vehicle3DViewerInner() {
  const selectedAssetId = useOperationsStore((s) => s.selectedAssetId);
  const asset = useOperationsStore((s) =>
    s.selectedAssetId ? s.assetsById[s.selectedAssetId] : undefined
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const ctxRef = useRef<SceneContext | null>(null);

  const { data: assetCommands } = useAssetCommandsQuery(selectedAssetId);
  const latestCommand = assetCommands?.reduce<(typeof assetCommands)[number] | null>(
    (latest, current) =>
      !latest || Date.parse(current.updated_at) > Date.parse(latest.updated_at) ? current : latest,
    null
  );

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

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf2f2f2);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.01, 100);
    camera.position.set(1.1, 0.85, 1.1);
    camera.lookAt(0, 0, 0);

    scene.add(new THREE.AmbientLight(0xffffff, 0.7));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.7);
    dirLight.position.set(2, 3, 1.5);
    scene.add(dirLight);
    scene.add(new THREE.GridHelper(1.6, 8, 0xbbbbbb, 0xdddddd));

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

  // 텔레메트리 갱신: 자세만 반영하고 1프레임 렌더.
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

  const freshness = asset ? classifyFreshness(asset, Date.now()) : null;

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
      <div style={{ padding: "0.25rem 0.75rem", color: "gray", fontSize: "0.8em" }}>
        {latestCommand
          ? `최근 연관 명령: ${latestCommand.command_id} · ${latestCommand.status} · ${new Date(
              latestCommand.updated_at
            ).toLocaleTimeString()}`
          : "최근 연관 명령 없음"}
      </div>
    </div>
  );
}

/** 오류 경계로 감싼 공개 컴포넌트 — 3D 렌더 실패가 2D 관제를 중단시키지 않는다. */
export function Vehicle3DViewer() {
  return (
    <Vehicle3DErrorBoundary>
      <Vehicle3DViewerInner />
    </Vehicle3DErrorBoundary>
  );
}
