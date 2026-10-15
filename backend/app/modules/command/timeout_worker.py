"""단계별 기한(`expires_at`) 판정 백그라운드 task.

`docs/planning/02_백엔드_아키텍처.md` "명령 처리 규칙": "timeout worker가 승인·전달·ACK·
실행 단계별 기한을 판정한다." 이 프로젝트는 `CommandEnvelope`에 마감 시각이
`expires_at` 하나뿐이라(별도의 승인 기한/ACK 기한 필드는 없음), 전체 수명주기에 대한
단일 마감으로 두고 "그 시점에 어느 단계에서 멈춰 있었는지"를 이벤트에 남겨 구분한다.

`telemetry`의 consumer와 같은 패턴 — 앱 lifespan 동안 떠 있는 asyncio task 하나로
polling한다(ADR 0001, 별도 워커 프로세스를 두지 않는다).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.metrics import command_timeout_swept_total
from app.db.base import SessionLocal
from app.modules.command.models import Command
from app.modules.command.repository import force_timeout
from app.modules.command.state_machine import TERMINAL_STATUSES

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 5.0


def sweep_timed_out_commands() -> int:
    """만료됐지만 아직 종결 상태가 아닌 명령을 전부 TIMED_OUT으로 전이시킨다.

    동기 함수라 `asyncio.to_thread`에서 호출된다. 반환값은 처리 건수(로그·테스트용).
    """
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        stmt = select(Command).where(
            Command.expires_at < now, Command.status.notin_(TERMINAL_STATUSES)
        )
        expired = list(db.execute(stmt).scalars().all())
        for command in expired:
            force_timeout(db, command)
        # `_transition`이 이미 범용 `command_status_transition_total{status="TIMED_OUT"}`
        # 를 올리지만, 그건 승인 시점에 즉시 만료 판정되는 경우(approve_and_dispatch)와
        # 구분이 안 된다. 이 카운터는 "방치돼 워커가 쓸어간" 것만 따로 센다 — 운영상
        # "승인이 늦어서 죽는 명령이 얼마나 되는지"를 보는 데 의미가 다르다.
        command_timeout_swept_total.inc(len(expired))
        return len(expired)


async def run_timeout_worker() -> None:
    """`CancelledError`(앱 종료)로 멈출 때까지 주기적으로 스윕한다."""
    while True:
        try:
            count = await asyncio.to_thread(sweep_timed_out_commands)
            if count:
                logger.info("타임아웃 처리된 명령 %d건", count)
        except Exception:  # noqa: BLE001 — 한 번의 스윕 실패가 워커 전체를 죽이면 안 된다
            logger.exception("명령 타임아웃 스윕 실패")
        await asyncio.sleep(POLL_INTERVAL_S)
