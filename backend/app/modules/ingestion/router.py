"""`POST /telemetry` — 텔레메트리 수신.

책임(`docs/planning/02_백엔드_아키텍처.md`): 스키마·범위 검증(FastAPI가 `TelemetryFrame`으로
자동 수행), 이벤트 발행. 저장·최신 상태 갱신·중복 판정은 요청 경로에서 하지 않고
`app.modules.telemetry.consumer`가 비동기로 수행한다("오래 걸리는 처리를 요청 경로에서
실행하지 않는다").
"""
from datetime import datetime, timezone

from fastapi import APIRouter, status

from app.core.metrics import telemetry_received_total
from app.core.redis import get_telemetry_redis
from app.modules.ingestion.streams import TELEMETRY_STREAM
from app.schemas.telemetry import TelemetryFrame

router = APIRouter(tags=["ingestion"])


@router.post("/telemetry", status_code=status.HTTP_202_ACCEPTED)
async def ingest_telemetry(frame: TelemetryFrame) -> dict:
    """계약 검증을 통과한 프레임을 접수하고 Redis Stream에 발행한다.

    `received_at`은 클라이언트(시뮬레이터)가 무엇을 보냈든 서버 수신 시각으로 덮어쓴다
    ("원본 이벤트 시각과 서버 수신 시각을 모두 저장한다").
    """
    received_frame = frame.model_copy(update={"received_at": datetime.now(timezone.utc)})

    redis_client = get_telemetry_redis()
    await redis_client.xadd(TELEMETRY_STREAM, {"payload": received_frame.model_dump_json()})

    telemetry_received_total.labels(asset_id=frame.asset_id).inc()

    return {
        "status": "accepted",
        "asset_id": received_frame.asset_id,
        "sequence_no": received_frame.sequence_no,
    }
