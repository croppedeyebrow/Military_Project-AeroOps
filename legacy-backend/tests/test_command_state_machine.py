"""순수 로직 단위 테스트: Command 상태 전이 그래프(서비스 없이도 항상 통과)."""
import pytest

from app.modules.command.state_machine import (
    CANCELLABLE_STATUSES,
    TERMINAL_STATUSES,
    InvalidTransition,
    assert_transition_allowed,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("PENDING_APPROVAL", "APPROVED"),
        ("PENDING_APPROVAL", "CANCELLED"),
        ("PENDING_APPROVAL", "TIMED_OUT"),
        ("APPROVED", "DISPATCHED"),
        ("DISPATCHED", "ACKNOWLEDGED"),
        ("ACKNOWLEDGED", "EXECUTING"),
        ("EXECUTING", "SUCCEEDED"),
        ("EXECUTING", "FAILED"),
    ],
)
def test_allowed_transitions_pass(current, target):
    assert_transition_allowed(current, target)  # 예외 없이 통과해야 한다


@pytest.mark.parametrize(
    ("current", "target"),
    [
        ("PENDING_APPROVAL", "DISPATCHED"),  # 승인 단계를 건너뜀
        ("PENDING_APPROVAL", "EXECUTING"),
        ("DISPATCHED", "EXECUTING"),  # ACK를 건너뜀
        ("EXECUTING", "CANCELLED"),  # 실행 시작 후에는 취소 불가
        ("SUCCEEDED", "EXECUTING"),  # 터미널 상태에서 되돌아감
        ("CANCELLED", "APPROVED"),
    ],
)
def test_disallowed_transitions_raise(current, target):
    with pytest.raises(InvalidTransition):
        assert_transition_allowed(current, target)


def test_terminal_statuses_have_no_outgoing_transitions():
    from app.modules.command.state_machine import TRANSITIONS

    for status in TERMINAL_STATUSES:
        assert TRANSITIONS[status] == frozenset()


def test_cancellable_statuses_exclude_executing_and_terminal():
    assert "EXECUTING" not in CANCELLABLE_STATUSES
    assert CANCELLABLE_STATUSES.isdisjoint(TERMINAL_STATUSES)
