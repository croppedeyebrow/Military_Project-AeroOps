# AeroOps Simulator

가상 드론 10대의 텔레메트리를 생성해 backend로 전송하는 Python CLI.
`docs/planning/05_데이터엔지니어링_아키텍처.md`, `docs/roadmap/02_단계_데이터계약_시뮬레이터_Day03-04.md` 참고.

## 로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env
python -m simulator.main run --sink stdout --no-real-time --duration-sec 10
```

## CLI 옵션

`python -m simulator.main run --help`로 전체 목록을 볼 수 있다. 주요 옵션:

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--seed` | 42 (`SIMULATOR_SEED`) | 재현성을 위한 난수 시드 |
| `--num-drones` | 10 (`NUM_DRONES`) | 시뮬레이션할 드론 수 |
| `--frequency-hz` | 1.0 (`FREQUENCY_HZ`) | 텔레메트리 발행 주파수 |
| `--scenario` | circle | `circle`\|`straight`\|`waypoint` |
| `--duration-sec` | 60 | 생성할 구간 길이(초) |
| `--faults` | (없음) | `duplicate,delay,out_of_order,missing,gps_jump,disconnect,battery_drop` 중 쉼표로 조합(이산 방식 — 정확히 1건/1구간만 주입) |
| `--loss-rate` | 0.0 | 프레임별 독립 손실 확률(0~1, 연속 방식). `--faults`와 별개로 적용 |
| `--reorder-window` | 0 | 이 크기의 구간 단위로 순서를 섞는다(연속 방식, 0/1이면 미적용) |
| `--delay-min-shift` / `--delay-max-shift` | 5 / (무제한) | `delay` 장애의 지연 칸수 범위 |
| `--disconnect-min-duration` / `--disconnect-max-duration` | 5 / 15 | `disconnect` 장애의 단절 구간 길이(틱) 범위 |
| `--gps-jump-min-m` | 5000.0 | `gps_jump` 장애의 최소 점프 거리(m) |
| `--battery-drop-pct` | 25.0 | `battery_drop` 장애의 급락 폭(%p) |
| `--sink` | http (`SIMULATOR_SINK`) | `http`\|`stdout` |
| `--ingest-url` | `http://localhost:8000/telemetry` (`INGEST_URL`) | 수집 API 엔드포인트(3단계 이후 실제 동작) |
| `--real-time/--no-real-time` | real-time | `frequency_hz` 속도로 페이싱할지 여부 |

## 계약과 장애 시나리오

- 데이터 계약: [`simulator/simulator/contracts/telemetry.py`](simulator/contracts/telemetry.py),
  [`contracts/command.py`](simulator/contracts/command.py). 필드 정의는
  [`docs/api/telemetry_frame_dictionary.md`](../docs/api/telemetry_frame_dictionary.md),
  [`docs/api/command_envelope_dictionary.md`](../docs/api/command_envelope_dictionary.md).
- 비행 시나리오: [`simulator/simulator/scenarios/`](simulator/scenarios/) (원형·직선·경유지).
- 장애 주입: [`simulator/simulator/faults.py`](simulator/faults.py) — 이산 방식 7종(중복·지연·
  역순·결측·GPS 점프·통신단절·배터리 급락) + 연속/확률 방식 2종(패킷 손실률, 재정렬 윈도우).
  동일 seed + 동일 파라미터는 항상 동일한 sequence gap을 만든다
  (`faults.compute_sequence_gaps`로 확인 가능).
- 기체 측 Command 처리(순수 로직, CLI 미연결): [`simulator/simulator/command_handler.py`](simulator/command_handler.py) —
  `CommandEnvelope` 하나를 "받았을 때 어떻게 반응하는가"만 독립적으로 시뮬레이션. 단위
  테스트로만 검증됨 — 아래 `device_loop.py`가 실제로 쓰이는 쪽이다.
- 기체 측 Command **실시간 반응**(실제 `/commands` API 연결): [`simulator/simulator/device_loop.py`](simulator/device_loop.py)
  — `--real-time`이고 장애 주입이 없을 때 자동으로 켜지는 모드(실행 시 로그에
  `mode=reactive`로 표시). 매 틱 `GET /commands?status=DISPATCHED`를 조회해 내 드론에
  해당하는 명령을 ACK→EXECUTING까지 보고하고, 실제로 비행 경로를 바꾼다:
  - `RTL`: 본부(`generator.BASE_LAT`/`BASE_LON` — 판교) 좌표로 직선 비행 후 그 자리에서
    대기. 도착하면 명령이 `SUCCEEDED`로 보고된다.
  - `MOVE_TO`: payload의 `target_latitude`/`target_longitude`/(선택)`target_altitude_m`
    으로 비행. 좌표가 없으면 즉시 `FAILED`.
  - `LOITER`: 즉시 현재 위치에서 정지.
  - `ARM`/`DISARM`: DISARM되면 다음 ARM까지 제자리에 고정(움직이지 않음).
  - `SET_ALTITUDE`: 기체가 이미 임무경로를 벗어난 상태(RTL/MOVE_TO/LOITER 이후)일 때만
    적용 — 아직 원래 시나리오(SCENARIO) 비행 중이면 즉시 `FAILED`.
  - `SET_SPEED`: 이후 이동(RETURNING/MOVING_TO) 속도를 바꾼다.
  - 한 기체가 이미 처리 중인 명령이 있으면 새 명령은 그게 끝날 때까지 기다린다(동시에
    두 개를 처리하지 않는다).
  - 장애 주입(`--faults`/`--reorder-window`)과는 같이 쓸 수 없다(장애 주입은 "미리
    계산해둔 전체 시퀀스를 변형"하는 방식이라 "한 틱씩 계산하며 명령에 반응하는" 구조와
    전제가 다르다) — 그 경우 기존 사전계산 경로로 자동 전환되고(`mode=precomputed`),
    명령에는 반응하지 않는다.

2단계에서는 backend에 아직 `POST /telemetry`가 없으므로 `--sink stdout`으로 독립 검증한다.
3단계 이후 `--sink http`(기본값)로 실제 수집 API에 연결한다.

## `--no-real-time`으로 실제 backend에 보낼 때 주의

`--no-real-time`은 `duration-sec` 전체 구간의 프레임을 미리 다 만들어 즉시 전송한다. 즉
`event_time`이 실제 "지금"보다 미래인 프레임이 대부분이다. backend는
`received_at`(서버가 실제로 받은 시각) `>= event_time`을 계약으로 강제하므로
(`docs/api/telemetry_frame_dictionary.md`), 이런 프레임은 각 기체의 첫 틱(`sequence_no=0`,
`event_time`이 생성 시각과 같음)만 통과하고 나머지는 consumer가 거부한다(로그만 남고 저장되지
않음, `aeroops_telemetry_consumer_error_total` 메트릭 증가). 실제 backend로 여러 틱을
검증하려면 `--real-time`(기본값)을 쓰거나, `--no-real-time`은 `--sink stdout`과만 조합한다.
