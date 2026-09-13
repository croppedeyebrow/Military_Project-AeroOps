"""3단계 보정 완료 기준 검증: "Telemetry 계정으로 Command stream 쓰기가 거부된다".

`live_client` fixture가 앱을 기동하면서(lifespan) `ensure_channel_acl_users`로 Redis ACL
사용자를 등록한다 — 이 테스트들은 그 결과를 실제 Redis 서버에 대고 확인한다(실제
Postgres/Redis 필요, 없으면 스킵).
"""
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import NoPermissionError

from app.core.redis import get_command_redis, get_telemetry_redis
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
