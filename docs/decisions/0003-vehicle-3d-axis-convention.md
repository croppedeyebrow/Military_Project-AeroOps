# ADR 0003: 3D 뷰어 좌표축·자세(roll/pitch/yaw) 매핑 규칙

- 상태: 승인됨
- 일자: 2026-10-10

## 배경

6단계(`docs/roadmap/06_단계_3D상세뷰어_Day14-15.md`)에서 선택 기체를 three.js로 렌더링하며
`TelemetryFrame`의 `heading_deg`/`roll_deg`/`pitch_deg`/`yaw_deg`(항공 관례, 나침반/기체
좌표계)를 three.js의 좌표계(오른손계, Y-up, 기본 전방 `-Z`)로 변환해야 한다. 이 매핑을
문서화하지 않으면 회전 방향이 뒤집히는 버그를 코드 리뷰만으로 잡기 어렵다
(`docs/roadmap/작업분해_2단계_8단계.md` 6단계 "축 정의 문서 작성" 산출물).

시뮬레이터(`simulator/simulator/scenarios/*.py`)의 실제 생성 규칙 확인 결과:
`yaw_deg = to_signed_deg(heading_deg)` — 즉 MVP 범위에서 yaw는 진행방향(나침반 방위각)의
부호 있는[-180,180] 표현과 같다. `pitch_deg`는 현재 항상 0(향후 사용 대비 필드만 존재),
`roll_deg`는 선회 시 뱅크각(원 시나리오에서 `direction * BANK_ANGLE_DEG`)으로 쓰인다.

## 결정

### 장면 좌표계

| 축 | 의미 |
|---|---|
| `+X` | 동(East) |
| `+Y` | 상(Up, 고도 증가 방향) |
| `+Z` | 남(South) — 즉 `-Z`가 북(North) |

`heading_deg=0`(진북)일 때 모델의 "기수(nose)"가 기본적으로 `-Z`를 향하도록 모델을
배치한다(three.js 기본 카메라가 `-Z`를 바라보는 것과 맞물려 별도 카메라 보정 없이도
"위에서 내려다보면 북쪽이 화면 위"가 자연스럽게 성립).

### 회전 적용 순서

`THREE.Euler`의 `order: "YXZ"`를 사용한다 — three.js에서 이 순서는 회전행렬을
`R = Ry · Rx · Rz`로 구성하므로, **먼저 몸체 Z축 기준 회전(roll) → X축 기준 회전(pitch)
→ 마지막으로 월드 Y축 기준 회전(yaw)**이 적용된다. 이는 항공기 자세 표현의 표준 관례
(yaw → pitch → roll을 외재적으로 적용한 것과 동치인, 몸체 기준 roll → pitch → yaw 내재적
적용)와 일치한다.

### 각 성분과 부호

| 필드 | three.js Euler 성분 | 변환식 | 비고 |
|---|---|---|---|
| `heading_deg`/`yaw_deg` | `y` | `-radians(heading_deg)` | 나침반(시계방향 증가)을 Y축 양의 방향(반시계, 위에서 볼 때)과 맞추려면 부호 반전 필요 |
| `pitch_deg` | `x` | `+radians(pitch_deg)` | 양수 = 기수 상승(항공 관례) → 전방벡터의 +Y 성분 증가, 반전 불요 |
| `roll_deg` | `z` | `-radians(roll_deg)` | 양수 = 우익 하강(항공 관례) → 우측 벡터의 -Y 성분 증가시키려면 부호 반전 필요 |

```ts
const euler = new THREE.Euler(
  THREE.MathUtils.degToRad(pitch_deg ?? 0),
  -THREE.MathUtils.degToRad(heading_deg ?? yaw_deg ?? 0),
  -THREE.MathUtils.degToRad(roll_deg ?? 0),
  "YXZ"
);
mesh.quaternion.setFromEuler(euler);
```

### 검증 기준(자세 동기화 테스트가 확인하는 것)

- 기준 자세(`heading=0, pitch=0, roll=0`): 전방벡터 `(0,0,-1)`(북), 상방벡터 `(0,1,0)`.
- `heading=90`(동): 전방벡터가 `(1,0,0)`에 근접해야 한다(기수가 동쪽을 향함).
- `pitch=+30`(기수 상승): 전방벡터의 Y 성분이 양수여야 한다.
- `roll=+30`(우익 하강): 우측벡터(`forward × up` 기준 계산)의 Y 성분이 음수여야 한다.
- 위 네 벡터 비교는 `frontend/src/components/Vehicle3DViewer/attitude.ts`의 순수 함수
  (`eulerFromAttitude`, `forwardVector`, `rightVector`, `upVector`)로 분리해 vitest로
  DOM/WebGL 없이 검증한다(렌더러를 띄우지 않고 쿼터니언 수학만 검증).

### 보조선(진행방향 vs 센서/기수 방향)

- **진행방향**(ground track) 보조선: `heading_deg`만 사용한 수평 화살표.
- **기수/센서 방향** 보조선: 전체 자세(roll/pitch/yaw)가 반영된 전방벡터 화살표.
- MVP 시뮬레이터는 `yaw_deg = heading_deg`로 생성하므로 현재는 두 선이 선회 중 뱅크각으로
  인한 기울기만 다르고 수평 방향은 거의 일치한다 — 두 보조선을 분리해두는 이유는 향후
  크랩각(crab angle)이 있는 시나리오를 추가해도 코드 변경 없이 바로 분리 표시되게 하기 위함.

## 근거

- 모델 자체(기하)와 자세 변환 로직을 분리해, 추후 실제 GLB로 교체해도(사용자 결정:
  "일단 Three.js 프리미티브로, 추후 GLB 교체") 이 ADR의 좌표계·부호 규칙은 모델 제작자가
  "기수가 로컬 `-Z`를 향하도록" 배치하는 한 그대로 재사용된다.
- `order: "YXZ"`는 짐벌락을 pitch(X)가 ±90°에 가까워질 때만 겪는다 — 계약상 `pitch_deg`
  범위가 `[-90,90]`으로 제한돼 있어 경계값 근처 외에는 문제가 되지 않는다.

## 영향

- GLB로 교체할 때 모델의 전방이 로컬 `-Z`가 아니면(예: 일부 에셋은 `+Z` 또는 `+X`가 전방)
  `Vehicle3DViewer`에서 모델 그룹에 추가로 정적 보정 회전을 적용해야 한다 — 그 정적 보정은
  이 ADR의 좌표계 규칙과 별개로 "에셋 전용 보정"으로 명시 주석과 함께 적용한다.

## 관련 문서

- [[06_단계_3D상세뷰어_Day14-15]]
- `docs/api/telemetry_frame_dictionary.md`
