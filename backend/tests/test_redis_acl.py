"""3단계 보정 완료 기준 검증: "Telemetry 계정으로 Command stream 쓰기가 거부된다".

`live_client` fixture가 앱을 기동하면서(lifespan) `ensure_channel_acl_users`로 Redis ACL
사용자를 등록한다 — 이 테스트들은 그 결과를 실제 Redis 서버에 대고 확인한다(실제
Postgres/Redis 필요, 없으면 스킵).
"""
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import AuthenticationError, NoPermissionError

from app.core.redis import (
    TELEMETRY_REDIS_USERNAME,
    get_command_redis,
    get_redis,
    get_telemetry_redis,
)
from app.core.redis_acl import xadd_with_acl_retry
from app.modules.command.streams import COMMAND_STREAM
from app.modules.ingestion.streams import TELEMETRY_STREAM


@pytest.mark.asyncio
async def test_telemetry_account_can_write_its_own_stream(live_client: TestClient):
    telemetry_client = get_telemetry_redis()
    message_id = await telemetry_client.xadd(TELEMETRY_STREAM, {"payload": "{}"})
    assert message_id


@pytest.mark.asyncio
async def test_command_account_can_write_its_own_stream(live_client: TestClient):
    command_client = get_command_redis()
    message_id = await command_client.xadd(COMMAND_STREAM, {"payload": "{}"})
    assert message_id


@pytest.mark.asyncio
async def test_telemetry_account_cannot_write_command_stream(live_client: TestClient):
    telemetry_client = get_telemetry_redis()
    with pytest.raises(NoPermissionError):
        await telemetry_client.xadd(COMMAND_STREAM, {"payload": "{}"})


@pytest.mark.asyncio
async def test_command_account_cannot_write_telemetry_stream(live_client: TestClient):
    command_client = get_command_redis()
    with pytest.raises(NoPermissionError):
        await command_client.xadd(TELEMETRY_STREAM, {"payload": "{}"})


@pytest.mark.asyncio
async def test_telemetry_account_cannot_read_command_stream(live_client: TestClient):
    telemetry_client = get_telemetry_redis()
    with pytest.raises(NoPermissionError):
        await telemetry_client.xrange(COMMAND_STREAM, "-", "+")


@pytest.mark.asyncio
async def test_xadd_with_acl_retry_recovers_after_acl_user_disappears(live_client: TestClient):
    """7단계 장애 시험(2026-10-16): Redis가 재시작되면(이 프로젝트의 dev compose는
    영속 볼륨이 없다) 앱 시작 시 1회만 등록한 ACL 사용자가 사라지고, 이후 모든 요청이
    `AuthenticationError`로 영구히 실패하던 버그를 재현·검증한다. `ACL DELUSER` +
    커넥션 풀 재연결 강제로 "Redis 재시작으로 사용자가 사라진 상태"를 재현한다.
    """
    telemetry_client = get_telemetry_redis()
    await telemetry_client.xadd(TELEMETRY_STREAM, {"payload": "{}"})

    admin = get_redis()
    await admin.execute_command("ACL", "DELUSER", TELEMETRY_REDIS_USERNAME)
    await telemetry_client.connection_pool.disconnect()

    # 재현 확인: 재시도 로직 없는 맨 xadd는 여전히 인증 실패한다.
    with pytest.raises(AuthenticationError):
        await telemetry_client.xadd(TELEMETRY_STREAM, {"payload": "{}"})

    message_id = await xadd_with_acl_retry(
        telemetry_client, TELEMETRY_STREAM, {"payload": "{}"}
    )
    assert message_id
