import * as THREE from "three";
import { forwardVector, headingGroundVector } from "./attitude";
import type { Attitude } from "./attitude";

const ORIGIN = new THREE.Vector3(0, 0, 0);

/**
 * 진행방향(ground track, heading만)과 기수/센서 방향(roll·pitch 포함 전체 자세) 보조선.
 * `docs/decisions/0003-vehicle-3d-axis-convention.md` "보조선" 절 참고 — MVP
 * 시뮬레이터는 `yaw_deg == heading_deg`라 평소엔 두 선이 거의 겹치고, 선회 중에는
 * roll(뱅크각)로 인한 기울기 차이만 보인다.
 */
export function buildDirectionGuides(): {
  group: THREE.Group;
  update: (attitude: Attitude) => void;
  dispose: () => void;
} {
  const group = new THREE.Group();
  group.name = "direction-guides";

  const groundArrow = new THREE.ArrowHelper(
    headingGroundVector(0),
    ORIGIN,
    0.6,
    0x3388ff,
    0.12,
    0.08
  );
  groundArrow.name = "heading-ground-track";

  const noseArrow = new THREE.ArrowHelper(forwardVector({ headingDeg: 0, rollDeg: 0, pitchDeg: 0 }), ORIGIN, 0.5, 0xff7700, 0.1, 0.07);
  noseArrow.name = "nose-sensor-direction";

  group.add(groundArrow, noseArrow);

  return {
    group,
    update(attitude) {
      groundArrow.setDirection(headingGroundVector(attitude.headingDeg));
      noseArrow.setDirection(forwardVector(attitude));
    },
    dispose() {
      groundArrow.dispose();
      noseArrow.dispose();
    },
  };
}
