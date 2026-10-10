"""재동기화 판단 로직.

`docs/planning/02_백엔드_아키텍처.md` "재동기화": 재연결 시 마지막 telemetry sequence →
기체 상태 snapshot → 미종결 command 목록 → 서버 상태 비교 → 충돌 정책 적용 순으로 수행한다.
기체 인증(mTLS)은 8단계 전까지 없으므로 이 단계에서는 생략한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.command.models import Command
from app.modules.command.state_machine import TERMINAL_STATUSES as TERMINAL_COMMAND_STATUSES
from app.modules.deployment.repository import append_event_log
from app.modules.sync.models import SyncSession
from app.modules.sync.schemas import MAX_LISTED_MISSING_SEQUENCE_NUMBERS, SyncRequest
from app.modules.telemetry.models import AssetLatestState
from app.modules.telemetry.repository import (
    ensure_asset_exists,
    get_latest_state,
    get_max_sequence_no,
)


@dataclass(frozen=True)
class SyncDecision:
    server_last_sequence_no: int | None
    sequence_gap_count: int
    missing_sequence_numbers: list[int]
    anomaly: str | None
    pending_command_ids: list[str]
    snapshot_reissued: bool
    latest_state: AssetLatestState | None


def _compute_sequence_gap(
    server_max_seq: int | None, reported_last_sequence_no: int
) -> tuple[int, list[int], str | None]:
    """기체가 보고한 마지막 송신 sequence와 서버 저장분을 비교한다.

    - 서버 저장분 < 보고값: 그 사이 번호들은 전송됐지만 서버가 못 받은 것 — 손실 구간.
    - 서버 저장분 > 보고값: 기체 쪽 카운터가 서버보다 뒤처져 있다(재부팅 등으로 로컬 상태
      리셋) — 손실이 아니라 별도 이상 징후로 표시한다.
    """
    if server_max_seq is None or reported_last_sequence_no == server_max_seq:
        return 0, [], None
    if reported_last_sequence_no > server_max_seq:
        gap = reported_last_sequence_no - server_max_seq
        missing = list(range(server_max_seq + 1, reported_last_sequence_no + 1))
        return gap, missing[:MAX_LISTED_MISSING_SEQUENCE_NUMBERS], None
    return 0, [], "device_behind_server"


def perform_sync(db: Session, asset_id: str, request: SyncRequest) -> SyncDecision:
    ensure_asset_exists(db, asset_id)

    server_max_seq = get_max_sequence_no(db, asset_id)
    gap_count, missing, anomaly = _compute_sequence_gap(server_max_seq, request.last_sequence_no)

    pending_command_ids = list(
        db.execute(
            select(Command.id).where(
                Command.target_asset_id == asset_id,
                Command.status.notin_(TERMINAL_COMMAND_STATUSES),
            )
        ).scalars()
    )

    snapshot_reissued = gap_count > 0 or anomaly is not None
    latest_state = get_latest_state(db, asset_id) if snapshot_reissued else None

    requested_at = datetime.now(timezone.utc)
    sync_session = SyncSession(
        asset_id=asset_id,
        requested_at=requested_at,
        reported_last_sequence_no=request.last_sequence_no,
        server_last_sequence_no=server_max_seq,
        sequence_gap_count=gap_count,
        reported_last_processed_command_id=request.last_processed_command_id,
        pending_command_ids=pending_command_ids,
        snapshot_reissued=snapshot_reissued,
        detail={
            "anomaly": anomaly,
            "state_version": request.state_version,
            "missing_sequence_numbers_truncated": len(missing)
            >= MAX_LISTED_MISSING_SEQUENCE_NUMBERS,
        },
    )
    db.add(sync_session)
    db.commit()
    # id가 DB에서 발급되는 자동증가 값이라 commit 이후에야 읽을 수 있다 — event_log의
    # stream_sequence로 재사용하려면 refresh가 필요하다(원래 코드엔 없었다: 이 값을
    # 호출부가 안 썼기 때문).
    db.refresh(sync_session)

    # 목적: 재동기화는 "장애 복구성"을 보여주는 핵심 장면이라(완료 기준 "재동기화
    # 성공률") event_log에도 남아야 재생 화면에서 "이 시점에 재연결·대조가 있었다"를
    # 보여줄 수 있다.
    append_event_log(
        db,
        event_time=requested_at,
        stream_sequence=sync_session.id,
        source_channel="sync",
        event_type="sync.PERFORMED",
        payload={
            "asset_id": asset_id,
            "sequence_gap_count": gap_count,
            "anomaly": anomaly,
            "snapshot_reissued": snapshot_reissued,
        },
    )

    return SyncDecision(
        server_last_sequence_no=server_max_seq,
        sequence_gap_count=gap_count,
        missing_sequence_numbers=missing,
        anomaly=anomaly,
        pending_command_ids=pending_command_ids,
        snapshot_reissued=snapshot_reissued,
        latest_state=latest_state,
    )
