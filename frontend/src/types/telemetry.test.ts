import { describe, expect, it } from "vitest";
import { classifyFreshness, type TelemetryFrame } from "./telemetry";

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
    heading_deg: null,
    roll_deg: null,
    pitch_deg: null,
    yaw_deg: null,
    battery_pct: 90,
    rssi_dbm: null,
    flight_mode: null,
    ...overrides,
  };
}

describe("classifyFreshness", () => {
  const baseTimeMs = Date.parse("2026-01-01T00:00:00Z");

  it("returns live just after an update", () => {
    const frame = makeFrame({ received_at: "2026-01-01T00:00:00Z" });
    expect(classifyFreshness(frame, baseTimeMs + 1_000)).toBe("live");
  });

  it("returns stale after 10s without an update", () => {
    const frame = makeFrame({ received_at: "2026-01-01T00:00:00Z" });
    expect(classifyFreshness(frame, baseTimeMs + 15_000)).toBe("stale");
  });

  it("returns disconnected after 60s without an update", () => {
    const frame = makeFrame({ received_at: "2026-01-01T00:00:00Z" });
    expect(classifyFreshness(frame, baseTimeMs + 61_000)).toBe("disconnected");
  });

  it("falls back to event_time when received_at is null", () => {
    const frame = makeFrame({ received_at: null, event_time: "2026-01-01T00:00:00Z" });
    expect(classifyFreshness(frame, baseTimeMs + 61_000)).toBe("disconnected");
  });
});
