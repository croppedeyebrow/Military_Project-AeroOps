"""애플리케이션 설정.

`docs/planning/04_인프라_네트워크_클라우드.md`의 운영 기준(환경변수 기반 secret 주입)을 따른다.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "postgresql+psycopg://aeroops:aeroops@localhost:5432/aeroops"
    redis_url: str = "redis://localhost:6379/0"

    # Command/Telemetry 채널 네임스페이스 분리(docs/planning/02_백엔드_아키텍처.md).
    telemetry_stream_name: str = "aeroops:telemetry:raw"
    telemetry_consumer_group: str = "telemetry-processors"
    command_stream_name: str = "aeroops:command:events"
    command_consumer_group: str = "command-processors"

    # 채널별 Redis ACL 계정(3단계 보정). 앱이 시작할 때 스스로 등록한다
    # (`app/core/redis_acl.py`) — 별도 redis.conf/ACL 파일 배포 없이 어디서나 동작한다.
    # 사용자명은 상수로 고정하고("telemetry"/"command"), 비밀번호만 설정으로 둔다.
    telemetry_redis_password: str = "telemetry-dev-pass"
    command_redis_password: str = "command-dev-pass"

    # 배포 메타데이터(deployment 모듈, GET /system/build-info). CI/Docker 빌드가 주입한다.
    git_sha: str = "local-dev"
    image_tag: str = "local-dev"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
