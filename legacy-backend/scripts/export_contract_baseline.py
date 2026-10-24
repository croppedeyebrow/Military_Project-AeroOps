"""현행 FastAPI의 외부 계약을 `tests/contracts/baseline/`에 파일로 고정한다.

목적(ADR 0004, `docs/new_roadmap/01_기준선과_전환계약_Day01.md`): Kotlin C2 Core가 같은
REST/WebSocket/Redis Stream 계약을 내놓는지 비교할 기준선을 만든다. DB·Redis 없이
동작한다(앱 객체와 Pydantic 모델에서만 생성). 계약을 의도적으로 바꾼 경우에만
`python scripts/export_contract_baseline.py`로 다시 생성해 커밋한다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
BASELINE_DIR = BACKEND_DIR.parent / "tests" / "contracts" / "baseline"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def build_baseline() -> dict[str, dict]:
    """파일명 -> JSON 직렬화 가능한 계약 내용."""
    from app.main import app
    from app.modules.alert.schemas import AlertOut
    from app.modules.command.streams import COMMAND_CONSUMER_GROUP, COMMAND_STREAM
    from app.modules.ingestion.streams import CONSUMER_GROUP, TELEMETRY_STREAM
    from app.schemas.command import CommandEnvelope
    from app.schemas.telemetry import TelemetryFrame

    telemetry_schema = TelemetryFrame.model_json_schema()
    return {
        "openapi.json": app.openapi(),
        # `realtime/router.py`, `realtime/broadcaster.py`, `telemetry/consumer.py`의
        # 실제 전송 형태를 그대로 옮긴 것 — 연결 직후 snapshot 1회, 이후 update/alert.
        "websocket_messages.json": {
            "endpoint": "/ws/operations",
            "client_to_server": "없음(연결 종료 감지용 receive만 있음)",
            "server_to_client": {
                "snapshot": {
                    "type": "snapshot",
                    "assets": "TelemetryFrame[] (기체별 최신 상태)",
                    "alerts": "AlertOut[] (status=OPEN)",
                },
                "update": {"type": "update", "asset": "TelemetryFrame"},
                "alert": {"type": "alert", "alert": "AlertOut"},
            },
            "schemas": {
                "TelemetryFrame": telemetry_schema,
                "AlertOut": AlertOut.model_json_schema(),
            },
        },
        "redis_streams.json": {
            "telemetry": {
                "stream": TELEMETRY_STREAM,
                "consumer_group": CONSUMER_GROUP,
                "entry_fields": {
                    "payload": "TelemetryFrame JSON 문자열(received_at 서버 시각으로 덮어씀)"
                },
                "producer_user": "telemetry",
                "payload_schema": telemetry_schema,
            },
            "command": {
                "stream": COMMAND_STREAM,
                "consumer_group": COMMAND_CONSUMER_GROUP,
                "entry_fields": {"command_id": "str", "event_type": "DISPATCHED"},
                "producer_user": "command",
                "envelope_schema": CommandEnvelope.model_json_schema(),
            },
        },
    }


def render(content: dict) -> str:
    return json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> None:
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in build_baseline().items():
        (BASELINE_DIR / name).write_text(render(content), encoding="utf-8", newline="\n")
        print(f"wrote {BASELINE_DIR / name}")


if __name__ == "__main__":
    main()
