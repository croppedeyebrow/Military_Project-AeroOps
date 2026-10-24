"""이력 조회 다운샘플링 — 순수 함수로 분리해 DB/HTTP 없이 단위 테스트한다.

목적: `docs/roadmap/07_단계_이력재생_관측성_Day16-18.md` "이력 API 페이지 + 다운샘플링" —
재생 화면(`ReplayTimeline`/`TelemetryChart`)이 긴 시간 구간(예: 20분 × 1Hz = 1200개
프레임)을 차트로 그릴 때, 원본 1200개를 전부 내려보낼 필요가 없다. 화면 폭이 보통
수백~수천 픽셀이라 그 이상의 점은 그려봐야 겹쳐 보일 뿐이다.

근거(고정 stride를 고른 이유): 로드맵은 "고정 stride 또는 LTTB" 둘 다 허용한다. LTTB
(Largest-Triangle-Three-Buckets)는 각 버킷에서 "가장 시각적으로 중요한" 점을 골라
峰(peak)·급변 구간을 더 잘 보존하지만, 버킷팅 기준을 어떤 값(고도? 배터리? 위치?)으로
잡을지가 다중 series(위치/자세/배터리/RSSI가 한 프레임에 같이 있음) 상황에서 모호하다.
지금은 "균등하게 떨어진 점을 뽑되 양쪽 끝은 항상 포함한다"는 고정 stride 방식으로
충분하다 — 구현이 간단하고, 어떤 필드를 보든 결과가 일관적이다(필드별로 다른 버킷
기준을 적용하면 같은 timestamp에서 지도·3D·차트가 다른 점을 골랐을 수 있어 "동일
timestamp 일치" 완료 기준과 충돌할 수 있다). LTTB가 필요해지면(예: 배터리 급락처럼
짧은 급변을 자주 놓친다는 피드백이 생기면) 이 함수만 교체하면 된다 — 호출부
(`repository.py`)는 "레코드 리스트 → 레코드 리스트" 계약만 알고 있다.
"""
from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def downsample_fixed_stride(records: list[T], max_points: int) -> list[T]:
    """`records`(이미 시간순 정렬돼 있다고 가정)를 최대 `max_points`개로 줄인다.

    - `max_points <= 0`이거나 `len(records) <= max_points`면 원본을 그대로 반환한다
      (다운샘플링이 필요 없거나 무의미한 요청 — 호출부가 "항상 이 함수를 거쳐도 안전"
      하다고 가정할 수 있게 한다).
    - 그 외에는 0번째 인덱스와 마지막 인덱스를 **항상 포함**하고, 그 사이를 균등
      간격으로 채운다. 차트에서 구간의 시작과 끝이 빠지면 "전체 구간을 다 보고 있다"는
      신뢰를 깨뜨리기 때문에(실제로는 중간 어딘가에서 잘린 것처럼 보임) 양 끝은
      예외 없이 유지한다.
    """
    n = len(records)
    if max_points <= 0 or n <= max_points:
        return records
    if max_points == 1:
        return [records[-1]]

    stride = (n - 1) / (max_points - 1)
    # round()로 가장 가까운 정수 인덱스를 고른다. i=0 -> 0, i=max_points-1 -> n-1이
    # 수식으로 정확히 보장된다(끝점이 반올림 오차로 빠지는 일이 없다).
    indices = [round(i * stride) for i in range(max_points)]
    return [records[i] for i in indices]
