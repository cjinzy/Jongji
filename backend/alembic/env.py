"""Alembic 마이그레이션 환경 설정.

비동기 SQLAlchemy 엔진을 사용하여 마이그레이션을 실행합니다.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from jongji.config import settings
from jongji.database import Base
from jongji.models import *  # noqa: F401, F403 - 모든 모델을 import하여 Alembic이 감지하도록 함

# alembic.ini의 로깅 설정 적용
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 모든 모델의 메타데이터 참조 (자동 마이그레이션 생성용)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """오프라인 모드에서 마이그레이션 실행.

    DB 연결 없이 SQL 스크립트만 생성합니다.
    """
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """비동기 모드에서 마이그레이션 실행."""
    connectable = create_async_engine(settings.DATABASE_URL)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection) -> None:
    """동기 컨텍스트에서 마이그레이션 실행.

    Args:
        connection: 동기 DB 연결.
    """
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """온라인 모드에서 비동기 마이그레이션 실행."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
