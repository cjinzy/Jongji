"""MCP 공용 유틸리티 모듈.

FastMCP 인스턴스, DB 세션 팩토리, 인증 헬퍼, UUID 검증 함수를 제공합니다.
"""

import traceback
import uuid

from fastmcp import FastMCP
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from jongji.config import settings
from jongji.models.user import User, UserApiKey

mcp = FastMCP("Jongji MCP")

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


def validate_uuid(value: str, field_name: str) -> uuid.UUID:
    """UUID 문자열을 검증하고 UUID 객체로 변환합니다.

    Args:
        value: UUID 문자열.
        field_name: 검증 대상 필드 이름 (에러 메시지용).

    Returns:
        변환된 uuid.UUID 객체.

    Raises:
        ValueError: UUID 형식이 올바르지 않은 경우.
    """
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        msg = f"'{field_name}' 값이 유효한 UUID 형식이 아닙니다: {value!r}"
        logger.warning(msg)
        raise ValueError(msg) from exc


async def _get_user_by_api_key(api_key: str, db: AsyncSession) -> User | None:
    """API Key로 사용자를 조회합니다.

    활성 API Key를 순회하며 bcrypt로 비교하여 사용자를 반환합니다.

    Args:
        api_key: 평문 API 키.
        db: 비동기 DB 세션.

    Returns:
        User 객체 또는 None.
    """
    from jongji.services.auth_service import verify_password

    result = await db.execute(
        select(UserApiKey).where(UserApiKey.is_active.is_(True))
    )
    api_keys = result.scalars().all()

    for api_key_obj in api_keys:
        if await verify_password(api_key, api_key_obj.key_hash):
            user_result = await db.execute(
                select(User).where(User.id == api_key_obj.user_id, User.is_active.is_(True))
            )
            return user_result.scalar_one_or_none()

    return None


async def _require_user(api_key: str, db: AsyncSession) -> User:
    """API Key 인증 후 사용자를 반환합니다. 인증 실패 시 예외를 발생시킵니다.

    Args:
        api_key: 평문 API 키.
        db: 비동기 DB 세션.

    Returns:
        인증된 User 객체.

    Raises:
        PermissionError: API 키가 유효하지 않은 경우.
    """
    user = await _get_user_by_api_key(api_key, db)
    if not user:
        raise PermissionError("유효하지 않은 API 키입니다.")
    return user


def _handle_tool_error(tool_name: str, exc: Exception) -> dict:
    """MCP 도구 예외를 로깅하고 에러 응답을 반환합니다.

    Args:
        tool_name: 도구 함수 이름.
        exc: 발생한 예외.

    Returns:
        에러 메시지를 담은 딕셔너리.
    """
    logger.error(f"{tool_name} 실패: {traceback.format_exc()}")
    return {"error": "내부 오류가 발생했습니다."}
