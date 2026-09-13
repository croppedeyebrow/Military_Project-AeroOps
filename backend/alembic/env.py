"""Alembic 환경 설정.

`app.db.base.Base`의 metadata를 연결하고, `DATABASE_URL` 환경변수(`.env`로도 주입 가능,
`app.core.config.Settings` 참고)로 접속 URL을 결정한다.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402

# 모델을 import해야 Base.metadata에 테이블이 등록된다.
from app.modules.command import models as command_models  # noqa: E402, F401
from app.modules.deployment import models as deployment_models  # noqa: E402, F401
from app.modules.sync import models as sync_models  # noqa: E402, F401
from app.modules.telemetry import models as telemetry_models  # noqa: E402, F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
