# AeroOps Simulator

가상 드론 10대의 텔레메트리를 생성해 backend로 전송하는 Python CLI.
`docs/planning/05_데이터엔지니어링_아키텍처.md`, `docs/roadmap/02_단계_데이터계약_시뮬레이터_Day0304.md` 참고.

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
| `--faults` | (없음) | `duplicate,delay,out_of_order,missing,gps_jump,disconnect,battery_drop` 중 쉼표로 조합 |
| `--sink` | http (`SIMULATOR_SINK`) | `http`\|`stdout` |
| `--ingest-url` | `http://localhost:8000/telemetry` (`INGEST_URL`) | 수집 API 엔드포인트(3단계 이후 실제 동작) |
| `--real-time/--no-real-time` | real-time | `frequency_hz` 속도로 페이싱할지 여부 |

## 계약과 장애 시나리오

- 데이터 계약: [`simulator/simulator/contracts/telemetry.py`](simulator/contracts/telemetry.py),
  필드 정의는 [`docs/api/telemetry_frame_dictionary.md`](../docs/api/telemetry_frame_dictionary.md).
- 비행 시나리오: [`simulator/simulator/scenarios/`](simulator/scenarios/) (원형·직선·경유지).
- 장애 주입: [`simulator/simulator/faults.py`](simulator/faults.py) (7종: 중복·지연·역순·결측·
  GPS 점프·통신단절·배터리 급락).

2단계에서는 backend에 아직 `POST /telemetry`가 없으므로 `--sink stdout`으로 독립 검증한다.
3단계 이후 `--sink http`(기본값)로 실제 수집 API에 연결한다.
