"""댓글 관리 API 엔드포인트.

작업 댓글 CRUD와 @mention 기반 감시자 자동 등록을 제공합니다.
"""

import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user, get_db
from jongji.models.task import Task, TaskComment
from jongji.models.user import User
from jongji.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from jongji.services import comment_service

router = APIRouter(tags=["comments"])


@router.get("/api/v1/tasks/{task_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """작업의 댓글 목록을 반환합니다."""
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")

    return await comment_service.list_comments(task_id, db)


@router.post(
    "/api/v1/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    task_id: UUID,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """작업에 댓글을 작성합니다. @mention된 사용자는 자동으로 감시자로 등록됩니다."""
    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")

    try:
        return await comment_service.create_comment(task_id, current_user.id, data, db)
    except Exception:
        logger.error(f"댓글 생성 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 생성에 실패했습니다.",
        )


@router.put("/api/v1/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """댓글을 수정합니다. 작성자만 수정할 수 있습니다."""
    comment_result = await db.execute(select(TaskComment).where(TaskComment.id == comment_id))
    comment = comment_result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="댓글을 찾을 수 없습니다.")

    if comment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="댓글 수정 권한이 없습니다.")

    try:
        return await comment_service.update_comment(comment_id, data, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"댓글 수정 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 수정에 실패했습니다.",
        )


@router.delete("/api/v1/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """댓글을 삭제합니다. 작성자 또는 관리자만 삭제할 수 있습니다."""
    comment_result = await db.execute(select(TaskComment).where(TaskComment.id == comment_id))
    comment = comment_result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="댓글을 찾을 수 없습니다.")

    if comment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="댓글 삭제 권한이 없습니다.")

    try:
        await comment_service.delete_comment(comment_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"댓글 삭제 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="댓글 삭제에 실패했습니다.",
        )
