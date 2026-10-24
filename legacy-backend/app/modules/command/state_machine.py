"""Command 상태 전이 규칙.

`docs/planning/00_종합_기획서.md` "명령 수명주기":
`DRAFT → PENDING_APPROVAL → APPROVED → DISPATCHED → ACKNOWLEDGED → EXECUTING
→ SUCCEEDED/FAILED/TIMED_OUT/CANCELLED`

이 프로젝트의 `POST /commands`는 이미 승인을 구하는 완전한 요청이라 `DRAFT`를 거치지
않고 곧바로 `PENDING_APPROVAL`로 생성한다(`repository.py` 참고) — `DRAFT`는 나중에
"승인 요청 전 임시 저장" 기능이 필요해지면 쓸 자리로 남겨둔다.
"""
from __future__ import annotations

TRANSITIONS: dict[str, frozenset[str]] = {
    "DRAFT": frozenset({"PENDING_APPROVAL", "CANCELLED"}),
    "PENDING_APPROVAL": frozenset({"APPROVED", "CANCELLED", "TIMED_OUT"}),
    "APPROVED": frozenset({"DISPATCHED", "CANCELLED", "TIMED_OUT"}),
    "DISPATCHED": frozenset({"ACKNOWLEDGED", "CANCELLED", "TIMED_OUT"}),
    "ACKNOWLEDGED": frozenset({"EXECUTING", "CANCELLED", "TIMED_OUT"}),
    "EXECUTING": frozenset({"SUCCEEDED", "FAILED", "TIMED_OUT"}),
    "SUCCEEDED": frozenset(),
    "FAILED": frozenset(),
    "TIMED_OUT": frozenset(),
    "CANCELLED": frozenset(),
}

TERMINAL_STATUSES = frozenset({"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED"})

# "취소 버튼은 현재 상태에서 취소 가능한 경우에만 활성화한다"
# (docs/planning/01_프론트엔드_아키텍처.md). 실행이 시작되면(EXECUTING) 이미 되돌릴 수
# 없는 작업일 수 있어 취소 대상에서 뺀다.
CANCELLABLE_STATUSES = frozenset({"PENDING_APPROVAL", "APPROVED", "DISPATCHED", "ACKNOWLEDGED"})


class InvalidTransition(Exception):
    """허용되지 않는 상태 전이 시도."""


def assert_transition_allowed(current: str, target: str) -> None:
    allowed = TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise InvalidTransition(f"{current} -> {target} 전이는 허용되지 않는다")
