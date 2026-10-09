import * as THREE from "three";

/**
 * 저폴리곤 쿼드콥터 placeholder 지오메트리를 코드로 직접 생성한다.
 *
 * 사용자 결정(2026-10-10): 실제 GLB 모델은 라이선스 확인 후 추후 교체하고, 지금은
 * 외부 에셋·라이선스 표기가 전혀 필요 없는 Three.js 프리미티브로 자세(roll/pitch/yaw)
 * 검증과 UI를 먼저 완성한다. GLB로 교체 시 이 함수의 반환 그룹만 로더 결과로 바꾸면
 * 되고, `docs/decisions/0003-vehicle-3d-axis-convention.md`의 "기수=-Z" 규칙은
 * 유지해야 한다(에셋 전방이 다르면 그룹에 정적 보정 회전 추가).
 *
 * 그룹에 매단 geometry/material은 모두 이 함수가 생성한 전용 인스턴스이므로,
 * 기체 교체 시 `disposeDroneMesh`로 안전하게 해제할 수 있다.
 */
export function buildDroneMesh(): THREE.Group {
  const group = new THREE.Group();
  group.name = "drone-placeholder";

  const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0x3a3a3a });
  const armMaterial = new THREE.MeshStandardMaterial({ color: 0x5a5a5a });
  const propMaterial = new THREE.MeshStandardMaterial({ color: 0x1a1a1a });

  const body = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.08, 0.3), bodyMaterial);
  body.name = "body";
  group.add(body);

  const armLength = 0.42;
  const armPositions: Array<[number, number]> = [
    [1, 1],
    [-1, 1],
    [1, -1],
    [-1, -1],
  ];

  for (const [sx, sz] of armPositions) {
    const arm = new THREE.Mesh(
      new THREE.CylinderGeometry(0.015, 0.015, armLength, 8),
      armMaterial
    );
    arm.name = "arm";
    // 실린더 기본 축은 +Y — 수평 암으로 눕힌 뒤 대각선 방향으로 회전.
    arm.rotation.z = Math.PI / 2;
    arm.rotation.y = Math.atan2(sz, sx);
    arm.position.set((sx * armLength) / 2, 0, (sz * armLength) / 2);
    group.add(arm);

    const prop = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.008, 16), propMaterial);
    prop.name = "propeller";
    prop.position.set(sx * armLength * 0.9, 0.05, sz * armLength * 0.9);
    group.add(prop);
  }

  return group;
}

/** three.js는 geometry/material을 GC가 회수하지 않으므로 기체 전환·언마운트 시 명시 해제한다. */
export function disposeDroneMesh(group: THREE.Group): void {
  group.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry.dispose();
      const material = child.material;
      if (Array.isArray(material)) {
        material.forEach((m) => m.dispose());
      } else {
        material.dispose();
      }
    }
  });
}
