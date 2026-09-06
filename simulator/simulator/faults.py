"""장애 시나리오 주입기.

`docs/roadmap/02_단계_데이터계약_시뮬레이터_Day0304.md`: "중복·지연·역순·GPS 점프·단절
오류 주입", 완료 기준 "최소 6개 장애 시나리오 테스트가 통과한다".
`docs/planning/05_데이터엔지니어링_아키텍처.md`의 7개 장애 유형을 모두 구현한다.

각 함수는 한 기체의 정상 프레임 시퀀스(생성 순서 = `sequence_no` 오름차순)를 입력받아,
"전송 순서가 바뀌었거나 일부가 빠지거나 값이 이상해진" **에뮬레이트된 전송 스트림**을
반환한다. 계약(`TelemetryFrame` 필드 범위) 자체는 어기지 않는다 — 계약 위반은 별도로
`backend`의 검증 테스트에서 다룬다. 값 정의는 `docs/api/telemetry_frame_dictionary.md`
"장애 시나리오와의 관계" 표 참고.
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


def inject_delay(frames: list[TelemetryFrame], rng: np.random.Generator, min_shift: int = 5) -> list[TelemetryFrame]:
    """한 프레임을 원래 위치보다 한참 뒤(늦은 도착)로 밀어낸다. event_time은 바꾸지 않는다."""
    if len(frames) <= min_shift + 1:
        return frames
    result = list(frames)
    idx = int(rng.integers(0, len(result) - min_shift - 1))
    shift = int(rng.integers(min_shift, len(result) - idx))
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
    frames: list[TelemetryFrame], fault_types: list[str], rng: np.random.Generator
) -> list[TelemetryFrame]:
    """지정된 장애 유형들을 순서대로 적용한다. 미지원 유형은 즉시 오류로 알린다."""
    result = frames
    for fault_type in fault_types:
        if fault_type not in _INJECTORS:
            raise ValueError(f"알 수 없는 장애 유형: {fault_type} (지원: {', '.join(FAULT_TYPES)})")
        result = _INJECTORS[fault_type](result, rng)
    return result
