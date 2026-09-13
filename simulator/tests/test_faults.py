"""6종 이상 장애 시나리오 주입이 의도한 효과를 내는지 검증한다."""
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from simulator.contracts.telemetry import TelemetryFrame
from simulator.faults import (
    FAULT_TYPES,
    apply_faults,
    apply_packet_loss,
    apply_reorder_window,
    compute_sequence_gaps,
    inject_battery_drop,
    inject_delay,
    inject_disconnect,
    inject_duplicate,
    inject_gps_jump,
    inject_missing,
    inject_out_of_order,
)

START_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _clean_frames(count: int = 30) -> list[TelemetryFrame]:
    return [
        TelemetryFrame(
            asset_id="drone-01",
            event_time=START_TIME + timedelta(seconds=i),
            sequence_no=i,
            latitude=37.5,
            longitude=127.0 + i * 0.0001,
            altitude_m=100.0,
            battery_pct=95.0 - i * 0.01,
        )
        for i in range(count)
    ]


def _rng(seed: int = 1) -> np.random.Generator:
    return np.random.default_rng(seed)


def test_duplicate_repeats_a_sequence_number():
    frames = inject_duplicate(_clean_frames(), _rng())
    sequence_numbers = [f.sequence_no for f in frames]
    assert len(sequence_numbers) == len(set(sequence_numbers)) + 1


def test_delay_moves_a_frame_later_without_changing_event_time():
    clean = _clean_frames()
    delayed = inject_delay(clean, _rng(), min_shift=5)
    clean_ids = [f.sequence_no for f in clean]
    delayed_ids = [f.sequence_no for f in delayed]
    assert delayed_ids != clean_ids
    assert sorted(delayed_ids) == sorted(clean_ids)  # 내용은 그대로, 순서만 바뀜


def test_out_of_order_swaps_adjacent_frames():
    clean = _clean_frames()
    reordered = inject_out_of_order(clean, _rng())
    diffs = [i for i, (a, b) in enumerate(zip(clean, reordered)) if a.sequence_no != b.sequence_no]
    assert len(diffs) == 2  # 정확히 한 쌍만 뒤바뀐다
    assert diffs[1] == diffs[0] + 1


def test_missing_drops_exactly_one_frame():
    clean = _clean_frames()
    result = inject_missing(clean, _rng())
    assert len(result) == len(clean) - 1


def test_gps_jump_creates_large_position_delta():
    from simulator.scenarios.base import horizontal_distance_m

    clean = _clean_frames()
    jumped = inject_gps_jump(clean, _rng(), min_jump_m=5000.0)
    distances = [
        horizontal_distance_m(a.latitude, a.longitude, b.latitude, b.longitude)
        for a, b in zip(clean, jumped)
    ]
    assert max(distances) >= 5000.0


def test_disconnect_removes_a_contiguous_block():
    clean = _clean_frames(count=30)
    result = inject_disconnect(clean, _rng(), min_gap=5, max_gap=10)
    assert 20 <= len(result) <= 25
    remaining_sequence_numbers = [f.sequence_no for f in result]
    # 남은 구간 자체는 여전히 원래 순서를 유지한다(연속 블록만 통째로 빠짐).
    assert remaining_sequence_numbers == sorted(remaining_sequence_numbers)


def test_battery_drop_creates_abnormal_drop():
    clean = _clean_frames()
    result = inject_battery_drop(clean, _rng(), drop_pct=25.0)
    diffs = [c.battery_pct - r.battery_pct for c, r in zip(clean, result)]
    assert max(diffs) >= 25.0 - 1e-6


def test_all_documented_fault_types_are_covered():
    # docs/api/telemetry_frame_dictionary.md "장애 시나리오와의 관계" 표와 일치해야 한다.
    assert set(FAULT_TYPES) == {
        "duplicate",
        "delay",
        "out_of_order",
        "missing",
        "gps_jump",
        "disconnect",
        "battery_drop",
    }


def test_apply_faults_chains_multiple_types():
    result = apply_faults(_clean_frames(), ["duplicate", "missing"], _rng())
    assert isinstance(result, list)
    assert all(isinstance(f, TelemetryFrame) for f in result)


def test_apply_faults_rejects_unknown_type():
    with pytest.raises(ValueError):
        apply_faults(_clean_frames(), ["not_a_real_fault"], _rng())


def test_apply_faults_passes_per_type_kwargs():
    # min_shift=25로 지정하면 30개 프레임 중 뒤로 25칸 이상 밀릴 자리가 거의 없다.
    result = apply_faults(_clean_frames(), ["delay"], _rng(), fault_kwargs={"delay": {"min_shift": 25}})
    assert len(result) == 30  # delay는 개수를 바꾸지 않는다


def test_apply_packet_loss_drops_roughly_expected_fraction():
    clean = _clean_frames(count=1000)
    result = apply_packet_loss(clean, _rng(), loss_rate=0.3)
    assert len(result) < len(clean)
    # 큰 표본에서는 30% ± 여유 범위 안에 들어야 한다(엄격한 통계 검정은 아님).
    dropped_fraction = 1 - len(result) / len(clean)
    assert 0.2 < dropped_fraction < 0.4


def test_apply_packet_loss_zero_rate_is_noop():
    clean = _clean_frames()
    assert apply_packet_loss(clean, _rng(), loss_rate=0.0) == clean


def test_apply_packet_loss_rejects_out_of_range_rate():
    with pytest.raises(ValueError):
        apply_packet_loss(_clean_frames(), _rng(), loss_rate=1.5)


def test_apply_reorder_window_keeps_same_frames_shuffled_within_window():
    clean = _clean_frames(count=12)
    result = apply_reorder_window(clean, _rng(), window_size=4)
    assert len(result) == len(clean)
    assert sorted(f.sequence_no for f in result) == sorted(f.sequence_no for f in clean)
    # 각 4개짜리 창 내부에서만 섞였는지 확인(창을 넘어가는 이동은 없어야 한다).
    for w in range(0, 12, 4):
        window_before = {f.sequence_no for f in clean[w : w + 4]}
        window_after = {f.sequence_no for f in result[w : w + 4]}
        assert window_before == window_after


def test_apply_reorder_window_size_one_is_noop():
    clean = _clean_frames()
    assert apply_reorder_window(clean, _rng(), window_size=1) == clean


def test_compute_sequence_gaps_detects_missing_numbers():
    clean = _clean_frames(count=10)
    with_gap = [f for f in clean if f.sequence_no not in (3, 4, 7)]
    assert compute_sequence_gaps(with_gap) == [3, 4, 7]


def test_compute_sequence_gaps_empty_when_no_gap():
    assert compute_sequence_gaps(_clean_frames(count=10)) == []


def test_same_seed_and_profile_reproduce_same_sequence_gaps():
    """2단계 보정 완료 기준: 동일 seed + 동일 장애 profile → 동일 sequence gap."""

    def _gaps_for_seed(seed: int) -> list[int]:
        frames = apply_packet_loss(_clean_frames(count=200), _rng(seed), loss_rate=0.2)
        return compute_sequence_gaps(frames)

    gaps_a = _gaps_for_seed(42)
    gaps_b = _gaps_for_seed(42)
    gaps_c = _gaps_for_seed(43)

    assert gaps_a == gaps_b
    assert gaps_a  # 손실이 실제로 있었어야 의미있는 비교다
    assert gaps_a != gaps_c
