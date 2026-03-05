"""헬스체크 API 라우터.

서버 및 데이터베이스 연결 상태를 확인하는 엔드포인트를 제공합니다.
"""

import traceback

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """항상 200을 반환하는 라이브니스 체크 엔드포인트.

    Returns:
        dict: {"status": "ok"}
    """
    return {"status": "ok"}


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """DB 커넥션을 확인하는 레디니스 체크 엔드포인트.

    Args:
        db: 비동기 DB 세션 (dependency injection).

    Returns:
        JSONResponse: DB 연결 성공 시 200, 실패 시 503.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        logger.error(f"DB 연결 체크 실패:\n{traceback.format_exc()}")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
