"""기체(디바이스) 측 Command 처리 시뮬레이션.

`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day03-04.md`: "Command ACK·실행 결과·마지막
처리 command_id 시뮬레이션". 실제 `/commands` API·dispatch 경로는 아직 없으므로
(3단계 보정에서 최소 골격, 5단계에서 완성), 여기서는 "기체가 `CommandEnvelope`를 하나
받았을 때 어떻게 반응하는가"만 독립적으로 시뮬레이션한다 — 나중에 실제 Command 채널이
붙으면 이 컴포넌트가 그 소비자가 된다.

재동기화(`docs/planning/05_데이터엔지니어링_아키텍처.md` "재동기화 데이터 규칙")를 위해
기체는 "마지막으로 처리한 command_id"를 항상 기억한다 — `last_processed_command_id` 참고.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from simulator.contracts.command import CommandEnvelope


@dataclass(frozen=True)
class CommandAck:
    """명령을 수신했음을 알리는 응답(dispatch 직후, 실행 전)."""

    command_id: str
    asset_id: str
    acknowledged_at: datetime


@dataclass(frozen=True)
class CommandResult:
    """명령 실행이 끝난 뒤의 최종 결과."""

    command_id: str
    asset_id: str
    status: str  # "SUCCEEDED" | "FAILED" | "TIMED_OUT"
    completed_at: datetime
    detail: str | None = None


@dataclass
class DeviceCommandHandler:
    """기체 한 대의 Command 처리 로직(시뮬레이션).

    `failure_rate`로 실행 실패를 확률적으로 재현한다 — 실제 기체의 실행 실패(배터리 부족,
    지오펜스 위반 등 5단계 규칙과 무관하게 "그냥 실패하는 경우")를 단순화한 모델이다.
    """

    asset_id: str
    rng: np.random.Generator
    failure_rate: float = 0.05
    last_processed_command_id: str | None = field(default=None, init=False)

    def acknowledge(self, command: CommandEnvelope, *, now: datetime | None = None) -> CommandAck:
        """명령을 수신했음을 ACK한다. 아직 실행하지는 않는다."""
        return CommandAck(
            command_id=command.command_id,
            asset_id=self.asset_id,
            acknowledged_at=now or datetime.now(timezone.utc),
        )

    def process(self, command: CommandEnvelope, *, now: datetime | None = None) -> CommandResult:
        """명령을 처리한다: 만료됐으면 TIMED_OUT, 아니면 확률적으로 성공/실패시킨다.

        어느 경우든 `last_processed_command_id`는 갱신된다 — 재동기화 시 서버가 "이 기체가
        어디까지 처리했는지" 조회할 수 있어야 하기 때문이다(만료로 실행을 안 했어도 "처리는
        했다"는 사실 자체가 중요하다).
        """
        now = now or datetime.now(timezone.utc)
        self.last_processed_command_id = command.command_id

        if now > command.expires_at:
            return CommandResult(
                command_id=command.command_id,
                asset_id=self.asset_id,
                status="TIMED_OUT",
                completed_at=now,
                detail=f"만료 시각({command.expires_at.isoformat()}) 이후 처리됨",
            )

        failed = bool(self.rng.random() < self.failure_rate)
        return CommandResult(
            command_id=command.command_id,
            asset_id=self.asset_id,
            status="FAILED" if failed else "SUCCEEDED",
            completed_at=now,
            detail="시뮬레이션 임의 실패" if failed else None,
        )
