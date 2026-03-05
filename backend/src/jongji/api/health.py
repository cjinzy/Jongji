"""헬스체크 API 라우터.

서버 및 데이터베이스 연결 상태를 확인하는 엔드포인트를 제공합니다.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """데이터베이스 연결을 포함한 헬스체크 엔드포인트.

    Args:
        db: 비동기 DB 세션 (dependency injection).

    Returns:
        dict: 서버 상태 정보.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}, 503


@router.get("/ready")
async def readiness_check():
    """서버 준비 상태 확인 엔드포인트.

    Returns:
        dict: 준비 상태 정보.
    """
    return {"status": "ready"}
