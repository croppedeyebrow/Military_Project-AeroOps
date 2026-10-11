import { describe, expect, it } from "vitest";
import type { TelemetryFrame } from "../../types/telemetry";
import type { ReplayDataset } from "../../types/replay";
import { buildAssetFramesAtTime, findFrameAtTime } from "./frameLookup";

function makeFrame(eventTime: string, sequenceNo: number): TelemetryFrame {
  return {
    schema_version: 1,
    asset_id: "drone-01",
    mission_id: null,
    event_time: eventTime,
    received_at: eventTime,
    sequence_no: sequenceNo,
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
  };
}

const FRAMES = [
  makeFrame("2026-01-01T00:00:00Z", 0),
  makeFrame("2026-01-01T00:00:10Z", 1),
  makeFrame("2026-01-01T00:00:20Z", 2),
  makeFrame("2026-01-01T00:00:30Z", 3),
];

describe("findFrameAtTime", () => {
  it("빈 배열이면 null", () => {
    expect(findFrameAtTime([], Date.parse("2026-01-01T00:00:00Z"))).toBeNull();
  });

  it("첫 프레임보다 이른 시각이면 null(아직 데이터 없음)", () => {
    const t = Date.parse("2025-12-31T23:59:00Z");
    expect(findFrameAtTime(FRAMES, t)).toBeNull();
  });

  it("정확히 어떤 프레임의 event_time이면 그 프레임", () => {
    const t = Date.parse("2026-01-01T00:00:20Z");
    expect(findFrameAtTime(FRAMES, t)?.sequence_no).toBe(2);
  });

  it("두 프레임 사이 시각이면 그 이전(과거) 프레임을 반환", () => {
    const t = Date.parse("2026-01-01T00:00:15Z");
    expect(findFrameAtTime(FRAMES, t)?.sequence_no).toBe(1);
  });

  it("마지막 프레임보다 늦은 시각이면 마지막 프레임을 유지", () => {
    const t = Date.parse("2026-01-01T01:00:00Z");
    expect(findFrameAtTime(FRAMES, t)?.sequence_no).toBe(3);
  });

  it("단일 프레임 배열에서도 동작", () => {
    const single = [FRAMES[0]];
    expect(findFrameAtTime(single, Date.parse("2026-01-01T00:00:05Z"))?.sequence_no).toBe(0);
  });
});

describe("buildAssetFramesAtTime", () => {
  const OTHER_FRAMES = [makeFrame("2026-01-01T00:00:50Z", 0)];

  it("각 기체의 그 시각 프레임을 asset_id로 묶어 돌려준다", () => {
    const dataset: ReplayDataset = { "drone-01": FRAMES, "drone-02": OTHER_FRAMES };
    const t = Date.parse("2026-01-01T00:00:55Z"); // 둘 다 첫 프레임 이후라 둘 다 데이터가 있음
    const result = buildAssetFramesAtTime(dataset, t);
    expect(result["drone-01"].sequence_no).toBe(3);
    expect(result["drone-02"].sequence_no).toBe(0);
  });

  it("아직 데이터가 없는 기체는 결과에서 빠진다", () => {
    const dataset: ReplayDataset = { "drone-01": FRAMES, "drone-02": OTHER_FRAMES };
    const t = Date.parse("2026-01-01T00:00:15Z"); // drone-02의 첫 프레임(00:00:50)보다 이름
    const result = buildAssetFramesAtTime(dataset, t);
    expect(result["drone-02"]).toBeUndefined();
  });

  it("빈 데이터셋이면 빈 객체", () => {
    expect(buildAssetFramesAtTime({}, Date.now())).toEqual({});
  });
});
