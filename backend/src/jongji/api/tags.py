"""태그 API 엔드포인트.

프로젝트별 태그 목록 조회, 태그별 작업 조회를 제공합니다.
"""

import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_db, require_project_access
from jongji.models.user import User
from jongji.schemas.tag import TagResponse, TagTasksResponse
from jongji.services import tag_service

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(
    project_id: uuid.UUID,
    current_user: User = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 내 태그 목록을 사용 횟수와 함께 반환합니다.

    Args:
        project_id: 프로젝트 UUID (쿼리 파라미터).
        current_user: 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        TagResponse 목록 (count 내림차순).
    """
    try:
        tags = await tag_service.list_tags(project_id, db)
        return [TagResponse(tag=t["tag"], count=t["count"]) for t in tags]
    except Exception:
        logger.error(f"태그 목록 조회 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="태그 목록 조회에 실패했습니다.",
        )


@router.get("/{tag}/tasks", response_model=TagTasksResponse)
async def get_tasks_by_tag(
    tag: str,
    project_id: uuid.UUID,
    current_user: User = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """특정 태그가 붙은 작업 목록을 반환합니다.

    Args:
        tag: 태그 이름 ('#' 제외, 경로 파라미터).
        project_id: 프로젝트 UUID (쿼리 파라미터).
        current_user: 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        TagTasksResponse (tag + tasks 목록).
    """
    try:
        tasks = await tag_service.get_tasks_by_tag(tag, project_id, db)
        return TagTasksResponse(tag=tag, tasks=tasks)
    except Exception:
        logger.error(f"태그별 작업 조회 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="태그별 작업 조회에 실패했습니다.",
        )
