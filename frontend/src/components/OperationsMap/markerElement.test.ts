import { describe, expect, it } from "vitest";
import type { TelemetryFrame } from "../../types/telemetry";
import { createMarkerElement, FRESHNESS_COLOR, updateMarkerElement } from "./markerElement";

function makeFrame(overrides: Partial<TelemetryFrame> = {}): TelemetryFrame {
  return {
    schema_version: 1,
    asset_id: "drone-01",
    mission_id: null,
    event_time: "2026-01-01T00:00:00Z",
    received_at: "2026-01-01T00:00:00Z",
    sequence_no: 0,
    operation_session_id: null,
    deployment_id: null,
    correlation_id: null,
    latitude: 37.5,
    longitude: 127.0,
    altitude_m: 100,
    speed_mps: null,
    heading_deg: 90,
    roll_deg: null,
    pitch_deg: null,
    yaw_deg: null,
    battery_pct: 90,
    rssi_dbm: null,
    flight_mode: null,
    ...overrides,
  };
}

const NOW = Date.parse("2026-01-01T00:00:00Z");

// jsdom은 style.color를 읽을 때 hex를 rgb(...)로 정규화한다 — 같은 엔진으로 변환해서 비교한다.
function toRgb(hex: string): string {
  const probe = document.createElement("div");
  probe.style.color = hex;
  return probe.style.color;
}

describe("markerElement", () => {
  it("rotates the arrow to match heading_deg", () => {
    const el = createMarkerElement();
    updateMarkerElement(el, makeFrame({ heading_deg: 90 }), false, NOW + 1000);
    const arrow = el.querySelector('[data-role="arrow"]') as HTMLDivElement;
    expect(arrow.style.transform).toBe("rotate(90deg)");
  });

  it("colors the arrow green when live", () => {
    const el = createMarkerElement();
    const freshness = updateMarkerElement(el, makeFrame(), false, NOW + 1000);
    expect(freshness).toBe("live");
    const arrow = el.querySelector('[data-role="arrow"]') as HTMLDivElement;
    expect(arrow.style.color).toBe(toRgb(FRESHNESS_COLOR.live));
  });

  it("colors the arrow gray and shows elapsed time when disconnected", () => {
    const el = createMarkerElement();
    const freshness = updateMarkerElement(el, makeFrame(), false, NOW + 61_000);
    expect(freshness).toBe("disconnected");
    const arrow = el.querySelector('[data-role="arrow"]') as HTMLDivElement;
    const label = el.querySelector('[data-role="label"]') as HTMLSpanElement;
    expect(arrow.style.color).toBe(toRgb(FRESHNESS_COLOR.disconnected));
    expect(label.textContent).toContain("drone-01");
    expect(label.textContent).toContain("전");
  });

  it("applies a highlight filter when selected", () => {
    const el = createMarkerElement();
    updateMarkerElement(el, makeFrame(), true, NOW + 1000);
    const arrow = el.querySelector('[data-role="arrow"]') as HTMLDivElement;
    expect(arrow.style.filter).not.toBe("none");
  });
});
