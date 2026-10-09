import { describe, expect, it } from "vitest";
import {
  forwardVector,
  headingGroundVector,
  rightVector,
  upVector,
} from "./attitude";

function approxVec(
  v: { x: number; y: number; z: number },
  expected: { x: number; y: number; z: number },
  epsilon = 1e-6
) {
  expect(v.x).toBeCloseTo(expected.x, 5);
  expect(v.y).toBeCloseTo(expected.y, 5);
  expect(v.z).toBeCloseTo(expected.z, 5);
  void epsilon;
}

describe("attitude axis convention (ADR 0003)", () => {
  it("기준 자세(0,0,0)에서 기수는 북(-Z), 상방은 +Y", () => {
    const attitude = { headingDeg: 0, rollDeg: 0, pitchDeg: 0 };
    approxVec(forwardVector(attitude), { x: 0, y: 0, z: -1 });
    approxVec(upVector(attitude), { x: 0, y: 1, z: 0 });
  });

  it("heading=90(동)이면 기수가 +X(동)를 향한다", () => {
    const attitude = { headingDeg: 90, rollDeg: 0, pitchDeg: 0 };
    approxVec(forwardVector(attitude), { x: 1, y: 0, z: 0 });
  });

  it("heading=180(남)이면 기수가 +Z(남)를 향한다", () => {
    const attitude = { headingDeg: 180, rollDeg: 0, pitchDeg: 0 };
    approxVec(forwardVector(attitude), { x: 0, y: 0, z: 1 });
  });

  it("heading=270(서)이면 기수가 -X(서)를 향한다", () => {
    const attitude = { headingDeg: 270, rollDeg: 0, pitchDeg: 0 };
    approxVec(forwardVector(attitude), { x: -1, y: 0, z: 0 });
  });

  it("pitch=+30(기수 상승)이면 전방벡터 Y 성분이 양수", () => {
    const attitude = { headingDeg: 0, rollDeg: 0, pitchDeg: 30 };
    const forward = forwardVector(attitude);
    expect(forward.y).toBeGreaterThan(0);
  });

  it("pitch=-30(기수 하강)이면 전방벡터 Y 성분이 음수", () => {
    const attitude = { headingDeg: 0, rollDeg: 0, pitchDeg: -30 };
    const forward = forwardVector(attitude);
    expect(forward.y).toBeLessThan(0);
  });

  it("roll=+30(우익 하강)이면 우측벡터 Y 성분이 음수", () => {
    const attitude = { headingDeg: 0, rollDeg: 30, pitchDeg: 0 };
    const right = rightVector(attitude);
    expect(right.y).toBeLessThan(0);
  });

  it("roll=-30(좌익 하강)이면 우측벡터 Y 성분이 양수", () => {
    const attitude = { headingDeg: 0, rollDeg: -30, pitchDeg: 0 };
    const right = rightVector(attitude);
    expect(right.y).toBeGreaterThan(0);
  });

  it("headingGroundVector는 roll/pitch와 무관하게 항상 수평(Y=0)", () => {
    const ground = headingGroundVector(37);
    expect(ground.y).toBeCloseTo(0, 6);
    expect(ground.length()).toBeCloseTo(1, 6);
  });

  it("heading=0 진행방향 벡터는 기수 방향 벡터(자세 0)와 일치", () => {
    const ground = headingGroundVector(0);
    const forward = forwardVector({ headingDeg: 0, rollDeg: 0, pitchDeg: 0 });
    approxVec(ground, forward);
  });
});
