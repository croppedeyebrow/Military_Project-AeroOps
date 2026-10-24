# 현행 FastAPI 계약 기준선 (Contract Baseline)

Kotlin C2 Core 전환(ADR 0004)에서 "같은 계약을 내놓는가"를 비교하기 위한 고정 스냅샷이다.

| 파일 | 내용 |
|---|---|
| `openapi.json` | REST 30개 경로 전체(요청·응답 스키마 포함) |
| `websocket_messages.json` | `/ws/operations`의 snapshot/update/alert 메시지와 `TelemetryFrame`·`AlertOut` 스키마 |
| `redis_streams.json` | Telemetry/Command Stream 이름, consumer group, entry 필드, 발행 계정 |

## 갱신 규칙

- 파일은 `legacy-backend/scripts/export_contract_baseline.py`가 생성한다. 손으로 고치지 않는다.
- `legacy-backend/tests/test_contract_baseline.py`가 현행 코드와 이 파일의 차이를 감지해 실패한다.
- 계약을 **의도적으로** 바꿨을 때만 `cd legacy-backend && python scripts/export_contract_baseline.py`로
  다시 만들고, 변경 이유를 커밋 메시지에 남긴다.
- 최종 Asset/Command/Alert/Audit 결과 기준선은 `../golden/`과 `../replay/`를 본다
  (`../README.md`).
