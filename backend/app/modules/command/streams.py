"""Redis Streams 이름·소비자 그룹 상수(Command 채널).

Telemetry 채널(`app.modules.ingestion.streams`)과 물리적으로 분리한다 —
`docs/planning/02_백엔드_아키텍처.md` "채널 및 권한 분리". 값은
`app.core.config.Settings`에서 오므로 `.env`로 오버라이드할 수 있다.
"""
from app.core.config import get_settings

_settings = get_settings()

COMMAND_STREAM = _settings.command_stream_name
COMMAND_CONSUMER_GROUP = _settings.command_consumer_group
COMMAND_CONSUMER_NAME = "worker-1"
