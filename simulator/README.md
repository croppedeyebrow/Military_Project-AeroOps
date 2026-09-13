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
- 기체 측 Command 처리: [`simulator/simulator/command_handler.py`](simulator/command_handler.py) —
  ACK, 실행 결과(성공/실패/타임아웃), `last_processed_command_id` 추적. 실제 `/commands` API가
  없으므로(3단계 보정 이후) 아직 CLI에 연결되어 있지는 않다 — 단위 테스트로만 검증됨.

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
