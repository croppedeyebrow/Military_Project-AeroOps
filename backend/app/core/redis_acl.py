"""Telemetry/Command 채널용 Redis ACL 사용자를 앱이 스스로 등록한다.

3단계 보정(`docs/roadmap/작업분해_2단계_8단계.md`) 완료 기준: "Telemetry 계정으로 Command
stream 쓰기가 거부된다". 별도 `redis.conf`/ACL 파일을 인프라에 배포하는 대신, 앱 시작 시
`ACL SETUSER`로 두 사용자를 만든다 — 로컬 개발·CI·docker-compose 어디서나 Redis 이미지를
그대로 써도 동작한다(vanilla `redis:7-alpine`이면 충분).

각 사용자는 `~<stream>*` 키 패턴으로 자기 채널의 스트림에만 접근할 수 있고, 관리자
성격 명령(`+@admin`, `+@dangerous`)은 제외한다. `reset`으로 매번 규칙을 새로 적용해
반복 호출해도(재시작 등) 항상 같은 최종 상태가 되게 한다(멱등).

프로덕션에서는 관리형 Redis가 ACL 명령 실행 권한을 기본 사용자에게 주지 않을 수 있다 —
그런 환경에서는 이 함수가 예외를 던지고, 호출부(`app/main.py`)가 경고만 남기고 계속
진행한다(채널 분리가 강제되지 않을 뿐 서비스 자체는 막지 않는다). 8단계에서 mTLS와 함께
운영 환경의 ACL 관리 방식을 재검토한다.
"""
import logging
from typing import Any

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.config import get_settings
from app.core.redis import COMMAND_REDIS_USERNAME, TELEMETRY_REDIS_USERNAME, get_redis

logger = logging.getLogger(__name__)


async def ensure_channel_acl_users(redis_client: redis.Redis | None = None) -> None:
    settings = get_settings()
    admin = redis_client or get_redis()

    await admin.execute_command(
        "ACL",
        "SETUSER",
        TELEMETRY_REDIS_USERNAME,
        "reset",
        "on",
        f">{settings.telemetry_redis_password}",
        f"~{settings.telemetry_stream_name}*",
        "+@all",
        "-@admin",
        "-@dangerous",
    )
    await admin.execute_command(
        "ACL",
        "SETUSER",
        COMMAND_REDIS_USERNAME,
        "reset",
        "on",
        f">{settings.command_redis_password}",
        f"~{settings.command_stream_name}*",
        "+@all",
        "-@admin",
        "-@dangerous",
    )
    logger.info(
        "Redis ACL 사용자 등록 완료: %s, %s", TELEMETRY_REDIS_USERNAME, COMMAND_REDIS_USERNAME
    )


async def xadd_with_acl_retry(
    redis_client: redis.Redis, stream: str, fields: dict[str, Any]
) -> str:
    """`AuthenticationError`(ConnectionError 하위)면 ACL을 재등록하고 한 번만 재시도하는 xadd.

    이 프로젝트의 dev `docker-compose`는 Redis에 영속 볼륨을 붙이지 않는다 — 그래서
    `docker stop`/`start`만으로도 Redis가 완전히 빈 상태로 돌아오고, 앱 시작 시 1회만
    등록한 `telemetry`/`command` ACL 사용자가 함께 사라진다. 7단계 장애 시험
    (2026-10-16)에서 Redis 재시작 이후 모든 텔레메트리 수신이 영구히 `AuthenticationError`로
    막히는 것을 실제로 확인했다 — 이 함수가 그 복구 경로다(재등록은 `reset`으로 매번
    같은 최종 상태를 만들어 멱등하므로 동시에 여러 요청이 재시도해도 안전하다).
    """
    try:
        return await redis_client.xadd(stream, fields)
    except RedisConnectionError:
        await ensure_channel_acl_users()
        return await redis_client.xadd(stream, fields)
