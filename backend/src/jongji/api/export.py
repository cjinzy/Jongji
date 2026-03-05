"""Export API 엔드포인트.

프로젝트 및 업무를 JSON 또는 Markdown 형식으로 내보냅니다.
"""

import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, Response
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user
from jongji.database import get_db
from jongji.models.user import User
from jongji.services import export_service

router = APIRouter(tags=["export"])


@router.get("/api/v1/projects/{project_id}/export")
async def export_project(
    project_id: uuid.UUID,
    fmt: str = Query("json", alias="format", pattern="^(json|markdown)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """프로젝트를 JSON 또는 Markdown으로 내보냅니다.

    Args:
        project_id: 프로젝트 UUID.
        fmt: 출력 형식 ("json" 또는 "markdown"), 기본값 "json".
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        fmt="json"이면 JSON 응답, fmt="markdown"이면 plain text 응답.

    Raises:
        HTTPException 404: 프로젝트 미존재.
        HTTPException 400: 잘못된 format.
    """
    try:
        result = await export_service.export_project(project_id, fmt, db)
    except ValueError as e:
        logger.warning(f"프로젝트 export 실패: {e}\n{traceback.format_exc()}")
        detail = str(e)
        if "찾을 수 없습니다" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if fmt == "markdown":
        return PlainTextResponse(content=result, media_type="text/markdown; charset=utf-8")
    return result


@router.get("/api/v1/tasks/{task_id}/export")
async def export_task(
    task_id: uuid.UUID,
    fmt: str = Query("json", alias="format", pattern="^(json|markdown)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """업무를 JSON 또는 Markdown으로 내보냅니다.

    Args:
        task_id: 업무 UUID.
        fmt: 출력 형식 ("json" 또는 "markdown"), 기본값 "json".
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        fmt="json"이면 JSON 응답, fmt="markdown"이면 plain text 응답.

    Raises:
        HTTPException 404: 업무 미존재.
        HTTPException 400: 잘못된 format.
    """
    try:
        result = await export_service.export_task(task_id, fmt, db)
    except ValueError as e:
        logger.warning(f"업무 export 실패: {e}\n{traceback.format_exc()}")
        detail = str(e)
        if "찾을 수 없습니다" in detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    if fmt == "markdown":
        return PlainTextResponse(content=result, media_type="text/markdown; charset=utf-8")
    return result
