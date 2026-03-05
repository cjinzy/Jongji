"""pytest 공통 픽스처 설정.

testcontainers를 사용하여 테스트용 PostgreSQL 컨테이너를 관리합니다.
"""

import pytest
from sqlalchemy import event as sa_event
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from jongji.database import Base
from jongji.models import *  # noqa: F401, F403 - 모든 모델을 로드하여 테이블 생성 보장

_schema_created = False


@pytest.fixture(scope="session")
def postgres_url():
    """세션 범위의 PostgreSQL 테스트 컨테이너 URL.

    Yields:
        str: asyncpg용 데이터베이스 연결 URL.
    """
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg")


@pytest.fixture
async def db_session(postgres_url):
    """테스트용 DB 세션 픽스처.

    매 테스트마다 새 엔진을 생성하여 이벤트 루프 문제를 방지합니다.
    첫 번째 테스트에서만 스키마를 생성합니다.

    Args:
        postgres_url: asyncpg 연결 URL.

    Yields:
        AsyncSession: 비동기 DB 세션.
    """
    global _schema_created
    engine = create_async_engine(postgres_url, echo=False)

    if not _schema_created:
        async with engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            await conn.run_sync(Base.metadata.create_all)
        _schema_created = True

    # connection-level 트랜잭션으로 감싸서 테스트 후 rollback으로 격리
    conn = await engine.connect()
    trans = await conn.begin()

    factory = async_sessionmaker(bind=conn, class_=AsyncSession, expire_on_commit=False)
    session = factory()

    # API의 get_db가 begin/commit을 호출해도 SAVEPOINT로 처리되도록 nested 사용
    nested = await conn.begin_nested()

    @sa_event.listens_for(session.sync_session, "after_transaction_end")
    def reopen_nested(session_sync, transaction):
        nonlocal nested
        if not conn.closed and not conn.invalidated and nested.is_active is False:
            nested = conn.sync_connection.begin_nested()

    yield session

    await session.close()
    await trans.rollback()
    await conn.close()
    await engine.dispose()
