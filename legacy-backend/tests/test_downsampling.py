"""순수 로직 단위 테스트: 이력 다운샘플링(서비스 없이도 항상 통과)."""
from app.modules.telemetry.downsampling import downsample_fixed_stride


def test_returns_original_when_already_within_limit():
    records = list(range(5))
    assert downsample_fixed_stride(records, max_points=10) == records


def test_returns_original_when_max_points_not_positive():
    records = list(range(5))
    assert downsample_fixed_stride(records, max_points=0) == records


def test_single_point_keeps_last_record():
    # 목적: max_points=1이면 "구간의 대표값 하나"가 필요한 경우다 — 첫 값보다 마지막
    # 값(가장 최신 상태)이 더 유용하다고 판단해 마지막을 남긴다.
    records = list(range(10))
    assert downsample_fixed_stride(records, max_points=1) == [9]


def test_always_includes_first_and_last():
    records = list(range(1000))
    result = downsample_fixed_stride(records, max_points=100)
    assert len(result) == 100
    assert result[0] == 0
    assert result[-1] == 999


def test_result_size_matches_max_points_exactly():
    records = list(range(97))  # 나누어 떨어지지 않는 길이로 반올림 경계를 확인
    result = downsample_fixed_stride(records, max_points=10)
    assert len(result) == 10


def test_result_is_monotonically_increasing_subset():
    # 목적: 균등 간격 선택이 순서를 뒤섞거나 중복시키지 않는지 확인(차트는 시간순을
    # 가정하므로 역전되면 그래프가 깨진다).
    records = list(range(123))
    result = downsample_fixed_stride(records, max_points=17)
    assert result == sorted(set(result))
