import { beforeEach, describe, expect, it } from "vitest";
import type { TelemetryFrame } from "../types/telemetry";
import { useOperationsStore } from "./useOperationsStore";

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

// 매 테스트 전 store를 초기 상태로 되돌린다(zustand store는 모듈 스코프에서 공유된다).
beforeEach(() => {
  useOperationsStore.setState({
    assetsById: {},
    connectionStatus: "connecting",
    lastReconnectedAt: null,
    selectedAssetId: null,
  });
});

describe("useOperationsStore", () => {
  it("applySnapshot replaces the whole asset map keyed by asset_id", () => {
    useOperationsStore.getState().applySnapshot([makeFrame({ asset_id: "a" }), makeFrame({ asset_id: "b" })]);
    const { assetsById } = useOperationsStore.getState();
    expect(Object.keys(assetsById).sort()).toEqual(["a", "b"]);
  });

  it("applyUpdate adds a new asset", () => {
    useOperationsStore.getState().applyUpdate(makeFrame({ asset_id: "a", sequence_no: 1 }));
    expect(useOperationsStore.getState().assetsById["a"].sequence_no).toBe(1);
  });

  it("applyUpdate overwrites when the new frame is newer", () => {
    useOperationsStore.getState().applyUpdate(
      makeFrame({ asset_id: "a", sequence_no: 1, event_time: "2026-01-01T00:00:01Z" })
    );
    useOperationsStore.getState().applyUpdate(
      makeFrame({ asset_id: "a", sequence_no: 2, event_time: "2026-01-01T00:00:02Z" })
    );
    expect(useOperationsStore.getState().assetsById["a"].sequence_no).toBe(2);
  });

  it("applyUpdate ignores an out-of-order (older) frame", () => {
    useOperationsStore.getState().applyUpdate(
      makeFrame({ asset_id: "a", sequence_no: 5, event_time: "2026-01-01T00:00:05Z" })
    );
    useOperationsStore.getState().applyUpdate(
      makeFrame({ asset_id: "a", sequence_no: 1, event_time: "2026-01-01T00:00:01Z" })
    );
    expect(useOperationsStore.getState().assetsById["a"].sequence_no).toBe(5);
  });

  it("markReconnected records a timestamp", () => {
    expect(useOperationsStore.getState().lastReconnectedAt).toBeNull();
    useOperationsStore.getState().markReconnected();
    expect(useOperationsStore.getState().lastReconnectedAt).not.toBeNull();
  });

  it("selectAsset updates the selection", () => {
    useOperationsStore.getState().selectAsset("a");
    expect(useOperationsStore.getState().selectedAssetId).toBe("a");
    useOperationsStore.getState().selectAsset(null);
    expect(useOperationsStore.getState().selectedAssetId).toBeNull();
  });
});
