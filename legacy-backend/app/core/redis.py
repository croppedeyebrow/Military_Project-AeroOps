"""Redis 클라이언트(Streams producer/consumer 공용).

`docs/planning/02_백엔드_아키텍처.md`의 처리 흐름: 수신 → 검증·정규화 →
스트림 발행 → 상태·경보 판정 / 배치 저장.

실제 서버는 이벤트 루프가 하나뿐이라 단순 전역 싱글턴이면 충분하지만, 테스트에서는
`TestClient(app)`를 `with`로 여닫을 때마다(또는 lifespan 없이 요청할 때마다) 서로 다른
이벤트 루프가 만들어진다. `asyncio.Redis` 커넥션은 만들어진 이벤트 루프에 묶이므로,
루프가 바뀌었는데 예전 루프에서 만든 클라이언트를 재사용하면 "Event loop is closed"로
깨진다. 그래서 실행 중인 이벤트 루프별로 클라이언트를 따로 캐싱한다.

3단계 보정: Telemetry/Command 채널을 물리적으로 분리하기 위해 채널별로 다른 Redis
사용자(ACL, `app/core/redis_acl.py`가 등록)를 쓰는 커넥션을 추가로 제공한다.
`get_redis()`(기본 사용자, 관리자 권한)는 health check·ACL 설정처럼 채널에 묶이지 않는
용도로만 쓴다 — 실제 텔레메트리/명령 발행·소비는 반드시 `get_telemetry_redis()`/
`get_command_redis()`를 쓴다.
"""
import asyncio
from urllib.parse import urlsplit, urlunsplit

import redis.asyncio as redis

from app.core.config import get_settings

TELEMETRY_REDIS_USERNAME = "telemetry"
COMMAND_REDIS_USERNAME = "command"

_clients_by_key: dict[tuple[int, str], redis.Redis] = {}


def _with_credentials(base_url: str, username: str, password: str) -> str:
    """`base_url`의 호스트·포트·DB는 유지하고 사용자/비밀번호만 바꾼 URL을 만든다."""
    parts = urlsplit(base_url)
    netloc = f"{username}:{password}@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _cached_client(cache_key: str, url: str) -> redis.Redis:
    loop = asyncio.get_event_loop()
    key = (id(loop), cache_key)
    client = _clients_by_key.get(key)
    if client is None:
        client = redis.from_url(url, decode_responses=True)
        _clients_by_key[key] = client
    return client


def get_redis() -> redis.Redis:
    """기본(관리자) 사용자 커넥션. health check, ACL 등록처럼 채널에 묶이지 않는 용도 전용."""
    return _cached_client("default", get_settings().redis_url)


def get_telemetry_redis() -> redis.Redis:
    """Telemetry 채널 전용 커넥션(`telemetry` ACL 사용자 — telemetry 스트림 키만 접근 가능)."""
    settings = get_settings()
    url = _with_credentials(
        settings.redis_url, TELEMETRY_REDIS_USERNAME, settings.telemetry_redis_password
    )
    return _cached_client("telemetry", url)


def get_command_redis() -> redis.Redis:
    """Command 채널 전용 커넥션(`command` ACL 사용자 — command 스트림 키만 접근 가능)."""
    settings = get_settings()
    url = _with_credentials(
        settings.redis_url, COMMAND_REDIS_USERNAME, settings.command_redis_password
    )
    return _cached_client("command", url)
