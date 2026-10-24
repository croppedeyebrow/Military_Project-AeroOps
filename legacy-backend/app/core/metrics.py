"""도메인 관측성 지표(Prometheus).

`docs/roadmap/03_단계_수집저장파이프라인_Day05-07.md`: "수신량·거부량·처리 지연 기본
메트릭 추가". 일반 HTTP 지표(`prometheus-fastapi-instrumentator`)와 별개로,
도메인에 의미 있는 카운터/히스토그램을 둔다.

7단계(`docs/roadmap/작업분해_2단계_8단계.md` "Prometheus 커스텀 메트릭"): 텔레메트리
파이프라인만 있던 걸 명령·실시간(WS)·경보·재동기화까지 넓힌다 — 이 네 영역은 각각
"정상적으로 동작하고 있다"는 걸 숫자로 보여줄 서로 다른 질문에 답한다: 명령은 "승인·
타임아웃이 얼마나 쌓이는가", 실시간은 "지금 몇 명이 보고 있는가", 경보는 "무슨 유형이
얼마나 자주 발생하는가", 재동기화는 "손실 구간이 보통 얼마나 큰가".
"""
from prometheus_client import Counter, Gauge, Histogram

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

# --- 명령(Command) ---

command_created_total = Counter(
    "aeroops_command_created_total",
    "새로 생성된 명령 수(멱등 재사용은 제외 — is_new=True인 경우만)",
    ["command_type"],
)

command_status_transition_total = Counter(
    "aeroops_command_status_transition_total",
    "명령이 도달한 상태별 전이 횟수(APPROVED/DISPATCHED/.../TIMED_OUT 등)",
    ["status"],
)

command_timeout_swept_total = Counter(
    "aeroops_command_timeout_swept_total",
    "timeout worker가 기한 초과로 강제 TIMED_OUT 처리한 명령 수",
)

# --- 실시간(WebSocket) ---

realtime_ws_connections = Gauge(
    "aeroops_realtime_ws_connections",
    "현재 연결된 /ws/operations 클라이언트 수",
)

realtime_broadcast_messages_total = Counter(
    "aeroops_realtime_broadcast_messages_total",
    "브로드캐스트된 메시지 수(연결된 클라이언트 수와 무관 — 발행 횟수 기준)",
    ["message_type"],
)

# --- 경보(Alert) ---

alert_raised_total = Counter(
    "aeroops_alert_raised_total",
    "새로 발생한 경보 수(같은 asset+type의 OPEN 경보가 이미 있으면 집계되지 않음 — "
    "`alert/repository.py`의 중복 방지 규칙과 동일)",
    ["alert_type", "severity"],
)

# --- 재동기화(Sync) ---

sync_performed_total = Counter(
    "aeroops_sync_performed_total",
    "재동기화(`POST /devices/{id}/sync`) 수행 횟수",
    ["anomaly"],  # "none" | "device_behind_server" 등 — sync/repository.py의 anomaly 값
)

sync_sequence_gap = Histogram(
    "aeroops_sync_sequence_gap",
    "재동기화 시 감지된 sequence gap 크기(0이면 손실 없음)",
    buckets=(0, 1, 5, 10, 50, 100, 500, 1000),
)
