"""장애 시나리오 주입기.

`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day03-04.md`: "중복·지연·역순·GPS 점프·단절
오류 주입", 완료 기준 "최소 6개 장애 시나리오 테스트가 통과한다".
`docs/planning/05_데이터엔지니어링_아키텍처.md`의 7개 장애 유형을 모두 구현한다.

각 함수는 한 기체의 정상 프레임 시퀀스(생성 순서 = `sequence_no` 오름차순)를 입력받아,
"전송 순서가 바뀌었거나 일부가 빠지거나 값이 이상해진" **에뮬레이트된 전송 스트림**을
반환한다. 계약(`TelemetryFrame` 필드 범위) 자체는 어기지 않는다 — 계약 위반은 별도로
`backend`의 검증 테스트에서 다룬다. 값 정의는 `docs/api/telemetry_frame_dictionary.md`
"장애 시나리오와의 관계" 표 참고.

2단계 보정(`docs/roadmap/작업분해_2단계_8단계.md`): "손실률·지연 분포·재정렬 윈도우·단절
시간을 설정값으로 제공"에 맞춰, 아래 두 가지 방식을 함께 제공한다.

- **이산 방식**(`inject_*`, `apply_faults`): 정확히 한 번(또는 한 구간)만 장애를 주입한다.
  결정론적이고 개별 테스트가 쉬워 "6개 이상 장애 시나리오 테스트" 검증에 적합하다.
- **연속/확률 방식**(`apply_packet_loss`, `apply_reorder_window`): 스트림 전체에 확률·윈도우
  기반으로 반복 적용해 실제 네트워크 손상에 더 가깝게 재현한다. `main.py`의 `--loss-rate`,
  `--reorder-window` 옵션이 이걸 쓴다.

두 방식 모두 같은 `rng`(seed로 초기화)를 받으므로, 동일 seed + 동일 파라미터는 항상 동일한
결과(및 동일한 sequence gap, `compute_sequence_gaps` 참고)를 만든다.
"""
from __future__ import annotations

import numpy as np

from simulator.contracts.telemetry import TelemetryFrame

FAULT_TYPES = (
    "duplicate",
    "delay",
    "out_of_order",
    "missing",
    "gps_jump",
    "disconnect",
    "battery_drop",
)


def inject_duplicate(frames: list[TelemetryFrame], rng: np.random.Generator) -> list[TelemetryFrame]:
    """임의의 한 프레임을 한 번 더(같은 asset_id+sequence_no) 내보낸다."""
    if not frames:
        return frames
    result = list(frames)
    idx = int(rng.integers(0, len(result)))
    insert_at = int(rng.integers(idx, len(result) + 1))
    result.insert(insert_at, result[idx])
    return result


def inject_delay(
    frames: list[TelemetryFrame],
    rng: np.random.Generator,
    min_shift: int = 5,
    max_shift: int | None = None,
) -> list[TelemetryFrame]:
    """한 프레임을 원래 위치보다 뒤(늦은 도착)로 밀어낸다. event_time은 바꾸지 않는다.

    `max_shift`(지연 분포의 상한)를 주지 않으면 기존처럼 리스트 끝까지 밀릴 수 있다.
    """
    if len(frames) <= min_shift + 1:
        return frames
    result = list(frames)
    idx = int(rng.integers(0, len(result) - min_shift - 1))
    upper = len(result) - idx if max_shift is None else min(max_shift + 1, len(result) - idx)
    if upper <= min_shift:
        return frames
    shift = int(rng.integers(min_shift, upper))
    frame = result.pop(idx)
    result.insert(idx + shift, frame)
    return result


def inject_out_of_order(frames: list[TelemetryFrame], rng: np.random.Generator) -> list[TelemetryFrame]:
    """인접한 두 프레임의 전송 순서를 맞바꾼다(짧은 네트워크 역전)."""
    if len(frames) < 2:
        return frames
    result = list(frames)
    idx = int(rng.integers(0, len(result) - 1))
    result[idx], result[idx + 1] = result[idx + 1], result[idx]
    return result


def inject_missing(frames: list[TelemetryFrame], rng: np.random.Generator) -> list[TelemetryFrame]:
    """단일 프레임 하나를 누락시킨다(결측)."""
    if not frames:
        return frames
    result = list(frames)
    idx = int(rng.integers(0, len(result)))
    result.pop(idx)
    return result


def inject_gps_jump(
    frames: list[TelemetryFrame], rng: np.random.Generator, min_jump_m: float = 5000.0
) -> list[TelemetryFrame]:
    """한 프레임의 위치를 물리적으로 불가능한 거리만큼 순간 이동시킨다."""
    if not frames:
        return frames
    result = list(frames)
    idx = int(rng.integers(0, len(result)))
    frame = result[idx]
    # 위도 1도 ≈ 111.32km. min_jump_m 이상 벌어지도록 위도를 이동시킨다.
    lat_shift = (min_jump_m + float(rng.uniform(0, 2000))) / 111_320.0
    new_lat = frame.latitude + lat_shift
    if new_lat > 90:
        new_lat = frame.latitude - lat_shift
    result[idx] = frame.model_copy(update={"latitude": max(-90.0, min(90.0, new_lat))})
    return result


def inject_disconnect(
    frames: list[TelemetryFrame], rng: np.random.Generator, min_gap: int = 5, max_gap: int = 15
) -> list[TelemetryFrame]:
    """연속된 구간 전체가 비는 통신 단절을 만든다."""
    if len(frames) <= max_gap:
        return frames
    result = list(frames)
    gap = int(rng.integers(min_gap, max_gap + 1))
    start = int(rng.integers(0, len(result) - gap))
    del result[start : start + gap]
    return result


def inject_battery_drop(
    frames: list[TelemetryFrame], rng: np.random.Generator, drop_pct: float = 25.0
) -> list[TelemetryFrame]:
    """한 프레임에서 배터리가 비정상적으로 급락하게 만든다(정상 소모율보다 훨씬 큼)."""
    if not frames:
        return frames
    result = list(frames)
    idx = int(rng.integers(0, len(result)))
    frame = result[idx]
    new_battery = max(0.0, frame.battery_pct - drop_pct)
    result[idx] = frame.model_copy(update={"battery_pct": round(new_battery, 2)})
    return result


_INJECTORS = {
    "duplicate": inject_duplicate,
    "delay": inject_delay,
    "out_of_order": inject_out_of_order,
    "missing": inject_missing,
    "gps_jump": inject_gps_jump,
    "disconnect": inject_disconnect,
    "battery_drop": inject_battery_drop,
}


def apply_faults(
    frames: list[TelemetryFrame],
    fault_types: list[str],
    rng: np.random.Generator,
    fault_kwargs: dict[str, dict] | None = None,
) -> list[TelemetryFrame]:
    """지정된 장애 유형들을 순서대로 적용한다. 미지원 유형은 즉시 오류로 알린다.

    `fault_kwargs`로 유형별 파라미터(예: `{"delay": {"min_shift": 10, "max_shift": 20}}`)를
    넘기면 각 `inject_*` 함수의 기본값을 덮어쓴다.
    """
    fault_kwargs = fault_kwargs or {}
    result = frames
    for fault_type in fault_types:
        if fault_type not in _INJECTORS:
            raise ValueError(f"알 수 없는 장애 유형: {fault_type} (지원: {', '.join(FAULT_TYPES)})")
        result = _INJECTORS[fault_type](result, rng, **fault_kwargs.get(fault_type, {}))
    return result


def apply_packet_loss(
    frames: list[TelemetryFrame], rng: np.random.Generator, loss_rate: float
) -> list[TelemetryFrame]:
    """각 프레임을 독립적으로 `loss_rate` 확률로 떨어뜨린다(연속적인 네트워크 손실 재현).

    `inject_missing`(정확히 1건만 제거)과 달리, 스트림 전체에 걸쳐 반복 적용되는 확률
    모델이다. `loss_rate=0`이면 항상 원본을 그대로 반환한다.
    """
    if not (0.0 <= loss_rate <= 1.0):
        raise ValueError("loss_rate는 0.0~1.0 사이여야 한다")
    if loss_rate == 0.0 or not frames:
        return list(frames)
    keep_mask = rng.random(len(frames)) >= loss_rate
    return [frame for frame, keep in zip(frames, keep_mask) if keep]


def apply_reorder_window(
    frames: list[TelemetryFrame], rng: np.random.Generator, window_size: int
) -> list[TelemetryFrame]:
    """`window_size`개씩 겹치지 않는 구간으로 나눠 각 구간 내부만 무작위로 섞는다.

    `inject_out_of_order`(인접 두 프레임만 맞바꿈)를 일반화한 버전이다. `window_size<=1`이면
    원본을 그대로 반환한다.
    """
    if window_size <= 1 or not frames:
        return list(frames)
    result: list[TelemetryFrame] = []
    for start in range(0, len(frames), window_size):
        window = list(frames[start : start + window_size])
        order = rng.permutation(len(window))
        result.extend(window[i] for i in order)
    return result


def compute_sequence_gaps(frames: list[TelemetryFrame]) -> list[int]:
    """장애 주입 후 스트림에 실제로 존재하는 `sequence_no` 집합을 바탕으로 빠진 번호를 구한다.

    재현성 검증("동일 seed·장애 profile → 동일 sequence gap")에 쓴다. 기준 범위는 관측된
    `sequence_no`의 [min, max]이다 — 스트림 시작·끝 자체가 잘려나간 경우까지 감지하지는
    않는다(그건 별도로 프레임 개수를 비교해서 확인한다).
    """
    if not frames:
        return []
    observed = {frame.sequence_no for frame in frames}
    return [seq for seq in range(min(observed), max(observed) + 1) if seq not in observed]
