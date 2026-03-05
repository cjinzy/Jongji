"""데이터베이스 연결 및 세션 관리 모듈.

SQLAlchemy async 엔진과 세션 팩토리를 설정하고,
FastAPI dependency로 사용할 get_db 함수를 제공합니다.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from jongji.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """SQLAlchemy 모델의 기본 클래스."""

    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency: DB 세션을 yield하고 사용 후 닫습니다.

    Yields:
        AsyncSession: 비동기 SQLAlchemy 세션.
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
