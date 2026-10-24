"""Redis Streams 이름·소비자 그룹 상수(Telemetry 채널).

producer(`ingestion.router`)와 consumer(`telemetry.consumer`)가 공유한다. Command 채널은
`app.modules.command.streams`로 물리적으로 분리한다(3단계 보정 — 채널 분리).
값은 `app.core.config.Settings`에서 오므로 `.env`로 오버라이드할 수 있다.
"""
from app.core.config import get_settings

_settings = get_settings()

TELEMETRY_STREAM = _settings.telemetry_stream_name
CONSUMER_GROUP = _settings.telemetry_consumer_group
# 단일 프로세스 모놀리스(ADR 0001) 기준 MVP. 다중 인스턴스로 늘리면 hostname 등으로 대체한다.
CONSUMER_NAME = "worker-1"
