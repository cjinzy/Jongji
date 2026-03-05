"""FastAPI 공통 dependency 모듈.

각 API 엔드포인트에서 재사용할 dependency 함수들을 정의합니다.
인증 관련 dependency는 worker-5가 구현 완료 시 교체될 수 있습니다.
"""

import traceback

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.config import settings
from jongji.database import get_db
from jongji.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """현재 인증된 사용자를 반환합니다.

    Bearer 토큰에서 사용자 ID를 추출하고 DB에서 조회합니다.

    Args:
        credentials: HTTP Bearer 인증 정보.
        db: 비동기 DB 세션.

    Returns:
        인증된 User 모델.

    Raises:
        HTTPException: 인증 실패 시 401 또는 403.
    """
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")

    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="잘못된 토큰입니다.")
    except JWTError:
        logger.warning(f"JWT 디코딩 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="잘못된 토큰입니다.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다.")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """관리자 권한을 검증합니다.

    Args:
        user: 현재 인증된 사용자.

    Returns:
        관리자인 User 모델.

    Raises:
        HTTPException: 관리자가 아닌 경우 403.
    """
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return user


__all__ = ["get_db", "get_current_user", "require_admin"]
