import * as THREE from "three";

/**
 * `roll_deg`/`pitch_deg`/`heading_deg`(또는 `yaw_deg`) → three.js 쿼터니언 변환.
 *
 * 좌표축·부호 규칙은 `docs/decisions/0003-vehicle-3d-axis-convention.md` 참고:
 * 장면 좌표계는 +X=동, +Y=상, +Z=남(-Z=북)이고, 기준 자세(모든 각도 0)에서 기수는
 * -Z(북)를 향한다. `THREE.Euler`의 "YXZ" 순서(roll → pitch → yaw 내재적 적용)를 쓴다.
 *
 * WebGL/DOM 없이 순수 함수로 분리해 vitest에서 쿼터니언 수학만 검증한다.
 */
export interface Attitude {
  headingDeg: number;
  rollDeg: number;
  pitchDeg: number;
}

export function eulerFromAttitude({ headingDeg, rollDeg, pitchDeg }: Attitude): THREE.Euler {
  return new THREE.Euler(
    THREE.MathUtils.degToRad(pitchDeg),
    -THREE.MathUtils.degToRad(headingDeg),
    -THREE.MathUtils.degToRad(rollDeg),
    "YXZ"
  );
}

export function quaternionFromAttitude(attitude: Attitude): THREE.Quaternion {
  return new THREE.Quaternion().setFromEuler(eulerFromAttitude(attitude));
}

const BASE_FORWARD = new THREE.Vector3(0, 0, -1);
const BASE_UP = new THREE.Vector3(0, 1, 0);
const BASE_RIGHT = new THREE.Vector3(1, 0, 0);

/** 기수(진행) 방향 벡터 — 전체 자세(roll/pitch/yaw)가 반영된 "센서 방향" 보조선용. */
export function forwardVector(attitude: Attitude): THREE.Vector3 {
  return BASE_FORWARD.clone().applyQuaternion(quaternionFromAttitude(attitude));
}

/** 동체 우측 방향 벡터 — roll 검증(우익 하강 시 -Y 성분)에 사용. */
export function rightVector(attitude: Attitude): THREE.Vector3 {
  return BASE_RIGHT.clone().applyQuaternion(quaternionFromAttitude(attitude));
}

/** 동체 상방 벡터. */
export function upVector(attitude: Attitude): THREE.Vector3 {
  return BASE_UP.clone().applyQuaternion(quaternionFromAttitude(attitude));
}

/**
 * 진행방향(ground track) 전용 벡터 — `heading_deg`만 반영한 수평 벡터.
 * roll/pitch가 섞인 `forwardVector`와 달리 항상 수평면(XZ)에 있다.
 */
export function headingGroundVector(headingDeg: number): THREE.Vector3 {
  return BASE_FORWARD.clone().applyAxisAngle(BASE_UP, -THREE.MathUtils.degToRad(headingDeg));
}
