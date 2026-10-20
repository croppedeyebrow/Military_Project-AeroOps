# Contract·Golden Replay (전환 기준선)

Kotlin C2 Core 전환(ADR 0004)에서 "현행 FastAPI와 같은 결과를 내는가"를 판정하는 기준선이다.

| 위치 | 무엇을 고정하나 | 어떻게 확인하나 |
|---|---|---|
| `baseline/` | REST(OpenAPI)·WebSocket 메시지·Redis Stream 계약 | `backend/tests/test_contract_baseline.py`(서비스 불필요) |
| `golden/fastapi_replay.json` | 같은 입력을 넣었을 때의 최종 결과 | `replay/run_golden_replay.py`(서비스 필요) |

## Golden Replay

- 입력: 시뮬레이터 고정 seed(42)·3대·60초·고정 시작 시각. 시나리오 11종 — 정상, 중복,
  지연, 역순, 누락, 단절, 배터리 급락(경보 없음/경보 발생), GPS 점프, 20% 손실, 5칸 재정렬.
  명령 7종 — 정상 수명주기, 본인 승인 거부, 멱등 재요청, 취소 후 승인, 승인 전 ACK(불법 전이),
  실행 실패, ACK 손실→TIMED_OUT.
- 결과: 기체별 최신 상태·저장된 프레임/sequence 목록·event-log 집계(중복·최신 미갱신 수)·경보,
  명령별 단계 응답코드·최종 상태·이벤트 이력·감사 기록. 서버가 정하는 시각·ID는 넣지 않는다.
- HTTP로만 호출하므로 FastAPI든 Kotlin이든 `--base-url`만 바꿔 같은 시험을 돌린다.

```bash
# 시뮬레이터 venv(numpy, httpx 필요)에서, 백엔드·Postgres·Redis를 띄운 상태로
python tests/contracts/replay/run_golden_replay.py --base-url http://localhost:8000          # 비교(불일치 시 diff, exit 1)
python tests/contracts/replay/run_golden_replay.py --base-url http://localhost:8000 --update # 의도한 변경일 때만 기준선 갱신
```

실행마다 임의 태그를 붙여 asset·command ID를 만들므로 비우지 않은 DB에서도 반복 실행된다
(같은 DB에서 두 번 연속 실행해 결과가 바이트 단위로 일치함을 확인했다).

## 아직 포함하지 않은 것

- **지오펜스 이탈·RSSI 저하 경보**: 지오펜스는 전역 데이터라 공용 DB를 오염시키고, 시뮬레이터가
  RSSI 급락을 만들지 못한다. 별도 격리 환경이 생기면 추가한다.
- **재동기화(`/devices/{id}/sync`)·운용 세션 재생(`/operation-sessions/{id}/replay`)**.
- **PENDING_APPROVAL 단계 timeout, 만료된 명령의 승인 시도**.
- 운용 중 시각(`received_at` 등)은 서버 시계에 의존해 비교 대상에서 제외했다.
