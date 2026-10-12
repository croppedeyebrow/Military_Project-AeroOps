import { theme } from "../../styles/theme";
import { classifyFreshness, type AssetFreshness, type TelemetryFrame } from "../../types/telemetry";
import { formatElapsed } from "./format";

/**
 * 마커 DOM 요소 생성·갱신(순수 DOM 조작이라 jsdom에서 MapLibre 없이도 단위 테스트한다).
 * 삼각형(진행 방향 아이콘)은 CSS 테두리 트릭으로 그린다 — heading_deg=0(N)일 때 위를
 * 향하고, `rotate()`가 시계방향이라 나침반 방향(0=N,90=E,시계방향)과 그대로 맞는다.
 */

// disconnected는 `theme.color.status.danger`(빨강)가 아니라 `neutral`(회색)을 쓴다 —
// `theme.ts` 상단 주석 참고: 기체 하나가 조용해진 것과 내 WS 연결이 끊긴 것은 심각도가
// 다르다.
export const FRESHNESS_COLOR: Record<AssetFreshness, string> = {
  live: theme.color.status.success,
  stale: theme.color.status.warning,
  disconnected: theme.color.status.neutral,
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
  // 다크 테마 전환(2026-10-12): 흰색 반투명이었던 라벨 배경은 어두운 지도 타일 위에서
  // 튀는 흰 스티커처럼 보여 패널 배경과 같은 계열의 짙은 반투명으로 바꿨다.
  label.style.background = "rgba(11, 20, 32, 0.75)";
  label.style.padding = "0 2px";
  el.appendChild(label);

  return el;
}

/**
 * 본부(HQ) 마커 — 사용자 결정(2026-10-12): 편대 출발지(성남 판교)를 지도에 고정 표시한다.
 * 기체 마커(삼각형, 자세에 따라 회전)와 혼동되지 않게 완전히 다른 모양(원형 배지 +
 * 집 이모지)을 쓴다 — 회전하지도, 상태에 따라 색이 바뀌지도 않는 정적 지형지물이라는
 * 것을 모양 자체로 드러낸다. 새 아이콘 라이브러리를 추가하지 않고 유니코드 이모지를
 * 쓴다(이 프로젝트의 기존 방침 — 방향 아이콘도 스프라이트 대신 CSS 삼각형으로 직접 그림).
 */
export function createHqMarkerElement(): HTMLDivElement {
  const el = document.createElement("div");
  el.title = "본부(HQ)";
  el.style.display = "flex";
  el.style.flexDirection = "column";
  el.style.alignItems = "center";
  el.style.gap = "2px";
  el.style.pointerEvents = "none"; // 클릭 선택 대상이 아니다 — 기체 마커와만 상호작용.

  const badge = document.createElement("div");
  badge.style.width = "22px";
  badge.style.height = "22px";
  badge.style.borderRadius = theme.radius.full;
  badge.style.background = theme.color.background.panel;
  badge.style.border = `2px solid ${theme.color.accent}`;
  badge.style.display = "flex";
  badge.style.alignItems = "center";
  badge.style.justifyContent = "center";
  badge.style.fontSize = "12px";
  badge.textContent = "🏠";
  el.appendChild(badge);

  const label = document.createElement("span");
  label.textContent = "본부";
  label.style.fontSize = "11px";
  label.style.color = theme.color.accent;
  label.style.background = "rgba(11, 20, 32, 0.75)";
  label.style.padding = "0 3px";
  label.style.borderRadius = "2px";
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
