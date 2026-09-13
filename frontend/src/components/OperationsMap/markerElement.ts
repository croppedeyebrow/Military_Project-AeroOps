import { classifyFreshness, type AssetFreshness, type TelemetryFrame } from "../../types/telemetry";
import { formatElapsed } from "./format";

/**
 * 마커 DOM 요소 생성·갱신(순수 DOM 조작이라 jsdom에서 MapLibre 없이도 단위 테스트한다).
 * 삼각형(진행 방향 아이콘)은 CSS 테두리 트릭으로 그린다 — heading_deg=0(N)일 때 위를
 * 향하고, `rotate()`가 시계방향이라 나침반 방향(0=N,90=E,시계방향)과 그대로 맞는다.
 */

export const FRESHNESS_COLOR: Record<AssetFreshness, string> = {
  live: "#2e8b57",
  stale: "#daa520",
  disconnected: "#808080",
};

export function createMarkerElement(): HTMLDivElement {
  const el = document.createElement("div");
  el.style.position = "relative";
  el.style.width = "0";
  el.style.height = "0";
  el.style.cursor = "pointer";

  const arrow = document.createElement("div");
  arrow.dataset.role = "arrow";
  arrow.style.width = "0";
  arrow.style.height = "0";
  arrow.style.borderLeft = "7px solid transparent";
  arrow.style.borderRight = "7px solid transparent";
  arrow.style.borderBottom = "14px solid currentColor";
  arrow.style.transformOrigin = "50% 60%";
  el.appendChild(arrow);

  const label = document.createElement("span");
  label.dataset.role = "label";
  label.style.position = "absolute";
  label.style.left = "10px";
  label.style.top = "-8px";
  label.style.fontSize = "11px";
  label.style.color = FRESHNESS_COLOR.disconnected;
  label.style.whiteSpace = "nowrap";
  label.style.background = "rgba(255,255,255,0.8)";
  label.style.padding = "0 2px";
  el.appendChild(label);

  return el;
}

export function updateMarkerElement(
  el: HTMLDivElement,
  asset: TelemetryFrame,
  selected: boolean,
  nowMs: number
): AssetFreshness {
  const freshness = classifyFreshness(asset, nowMs);
  const arrow = el.querySelector<HTMLDivElement>('[data-role="arrow"]');
  const label = el.querySelector<HTMLSpanElement>('[data-role="label"]');

  if (arrow) {
    arrow.style.color = FRESHNESS_COLOR[freshness];
    const heading = asset.heading_deg ?? 0;
    arrow.style.transform = `rotate(${heading}deg)`;
    arrow.style.filter = selected ? "drop-shadow(0 0 3px black)" : "none";
  }

  if (label) {
    if (freshness === "disconnected") {
      const lastSeenIso = asset.received_at ?? asset.event_time;
      const elapsedMs = nowMs - Date.parse(lastSeenIso);
      label.textContent = `${asset.asset_id} · ${formatElapsed(elapsedMs)}`;
      label.style.display = "inline";
    } else {
      label.textContent = asset.asset_id;
      label.style.display = "inline";
    }
  }

  el.title = `${asset.asset_id} (${freshness})`;
  return freshness;
}
