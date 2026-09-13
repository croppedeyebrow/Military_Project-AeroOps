"""텔레메트리 파이프라인 관측성 지표.

`docs/roadmap/03_단계_수집저장파이프라인_Day05-07.md`: "수신량·거부량·처리 지연 기본
메트릭 추가". 일반 HTTP 지표(`prometheus-fastapi-instrumentator`)와 별개로,
도메인에 의미 있는 카운터/히스토그램을 둔다.
"""
from prometheus_client import Counter, Histogram

telemetry_received_total = Counter(
    "aeroops_telemetry_received_total",
    "계약 검증을 통과해 Redis Stream에 발행된 텔레메트리 프레임 수",
    ["asset_id"],
)

telemetry_rejected_total = Counter(
    "aeroops_telemetry_rejected_total",
    "계약(범위) 위반으로 거부된 텔레메트리 요청 수",
)

telemetry_duplicate_total = Counter(
    "aeroops_telemetry_duplicate_total",
    "asset_id+sequence_no 중복으로 저장에서 무시된 프레임 수",
    ["asset_id"],
)

telemetry_consumer_error_total = Counter(
    "aeroops_telemetry_consumer_error_total",
    "consumer가 스트림에서 읽은 뒤 처리(재검증·저장)에 실패해 버려진 메시지 수. "
    "예: --no-real-time 시뮬레이터가 미래 event_time 프레임을 한꺼번에 보내"
    "received_at >= event_time 규칙을 위반하는 경우",
)

telemetry_processing_latency_seconds = Histogram(
    "aeroops_telemetry_processing_latency_seconds",
    "received_at부터 DB 반영 완료까지의 처리 지연(초)",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
