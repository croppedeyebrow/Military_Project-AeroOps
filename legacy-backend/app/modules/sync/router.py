"""`POST /devices/{asset_id}/sync` — 재연결 재동기화 handshake.

`docs/roadmap/04_단계_2D실시간관제_Day08-10.md`: 기체가 마지막 sequence·state_version·
마지막 처리 command_id를 보고하면, 서버가 저장 상태와 대조해 손실 구간(sequence gap)을
기록하고 미종결 명령 목록·snapshot 재발급 여부를 응답한다. 모든 판단은 `sync_sessions`에
남는다.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.modules.sync.repository import perform_sync
from app.modules.sync.schemas import SyncRequest, SyncResponse
from app.modules.telemetry.schemas import frame_from_record

router = APIRouter(prefix="/devices", tags=["sync"])


@router.post("/{asset_id}/sync", response_model=SyncResponse)
def sync_device(asset_id: str, request: SyncRequest, db: Session = Depends(get_db)) -> SyncResponse:
    decision = perform_sync(db, asset_id, request)
    return SyncResponse(
        asset_id=asset_id,
        server_last_sequence_no=decision.server_last_sequence_no,
        sequence_gap_count=decision.sequence_gap_count,
        missing_sequence_numbers=decision.missing_sequence_numbers,
        anomaly=decision.anomaly,
        pending_command_ids=decision.pending_command_ids,
        snapshot_reissued=decision.snapshot_reissued,
        latest_state=frame_from_record(decision.latest_state) if decision.latest_state else None,
    )
