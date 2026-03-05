"""전문 검색 API 엔드포인트."""

import uuid

from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user
from jongji.database import get_db
from jongji.models.enums import TaskStatus
from jongji.models.user import User
from jongji.schemas.search import SearchResponse
from jongji.services import search_service

router = APIRouter(tags=["search"])


@router.get("/api/v1/search")
async def search_tasks(
    q: str = Query(..., min_length=1, description="검색어"),
    project_id: uuid.UUID | None = Query(None, description="프로젝트 필터"),
    tag: str | None = Query(None, description="태그 필터"),
    status: TaskStatus | None = Query(None, description="상태 필터"),
    assignee_id: uuid.UUID | None = Query(None, description="담당자 필터"),
    priority: int | None = Query(None, ge=1, le=9, description="우선순위 필터"),
    limit: int = Query(20, ge=1, le=100, description="결과 수 제한"),
    offset: int = Query(0, ge=0, description="오프셋"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """전문 검색을 수행합니다.

    pg_trgm + tsvector를 사용하여 작업 제목/설명/댓글을 검색합니다.
    - 한국어: trigram 유사도 매칭
    - 영어: tsvector FTS + trigram 보완
    - tag:xxx 또는 #xxx: 태그 정확 일치
    - PROJ-42 패턴: 프로젝트 키+번호 정확 일치

    Args:
        q: 검색어.
        project_id: 프로젝트 UUID 필터.
        tag: 태그 필터.
        status: 작업 상태 필터.
        assignee_id: 담당자 UUID 필터.
        priority: 우선순위 필터 (1-9).
        limit: 최대 반환 결과 수.
        offset: 페이지 오프셋.
        user: 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        SearchResponse: 검색 결과.
    """
    logger.info(f"검색 요청: q={q!r} user={user.id}")
    return await search_service.search(
        q,
        project_id=project_id,
        tag=tag,
        status=status,
        assignee_id=assignee_id,
        priority=priority,
        limit=limit,
        offset=offset,
        db=db,
    )
