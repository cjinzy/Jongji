"""댓글 관리 서비스 레이어.

댓글 CRUD, @mention 추출, 감시자 자동 등록 등의 비즈니스 로직을 처리합니다.
"""

import re
import traceback
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.task import TaskComment, TaskWatcher
from jongji.models.user import User
from jongji.schemas.comment import CommentCreate, CommentUpdate


def extract_mentions(content: str) -> list[str]:
    """댓글 내용에서 @mention된 사용자 이름 목록을 추출합니다.

    Markdown 텍스트에서 '@username' 패턴을 찾아 반환합니다.

    Args:
        content: 댓글 내용 (Markdown).

    Returns:
        mention된 사용자 이름 목록 (중복 제거).
    """
    pattern = r"@([\w.-]+)"
    matches = re.findall(pattern, content)
    return list(dict.fromkeys(matches))


async def add_watchers(task_id: uuid.UUID, usernames: list[str], db: AsyncSession) -> None:
    """@mention된 사용자들을 작업 감시자로 자동 등록합니다.

    이미 감시자인 경우 중복 등록하지 않습니다.
    존재하지 않는 사용자명은 조용히 무시합니다.

    Args:
        task_id: 작업 UUID.
        usernames: @mention된 사용자 이름 목록.
        db: 비동기 DB 세션.
    """
    try:
        for username in usernames:
            user_result = await db.execute(select(User).where(User.name == username))
            user = user_result.scalar_one_or_none()
            if not user:
                continue

            existing = await db.execute(
                select(TaskWatcher).where(
                    TaskWatcher.task_id == task_id,
                    TaskWatcher.user_id == user.id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            watcher = TaskWatcher(task_id=task_id, user_id=user.id)
            db.add(watcher)

        await db.flush()
    except Exception:
        logger.error(f"감시자 등록 실패: {traceback.format_exc()}")
        raise


async def create_comment(
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    data: CommentCreate,
    db: AsyncSession,
) -> TaskComment:
    """댓글을 생성하고 @mention된 사용자를 감시자로 등록합니다.

    Args:
        task_id: 작업 UUID.
        user_id: 작성자 UUID.
        data: 댓글 생성 데이터.
        db: 비동기 DB 세션.

    Returns:
        생성된 TaskComment 모델.
    """
    try:
        comment = TaskComment(
            task_id=task_id,
            user_id=user_id,
            content=data.content,
        )
        db.add(comment)
        await db.flush()
        await db.refresh(comment)

        usernames = extract_mentions(data.content)
        if usernames:
            await add_watchers(task_id, usernames, db)

        return comment
    except Exception:
        logger.error(f"댓글 생성 실패: {traceback.format_exc()}")
        raise


async def list_comments(task_id: uuid.UUID, db: AsyncSession) -> list[TaskComment]:
    """작업의 댓글 목록을 생성 시각 오름차순으로 반환합니다.

    Args:
        task_id: 작업 UUID.
        db: 비동기 DB 세션.

    Returns:
        TaskComment 목록.
    """
    result = await db.execute(
        select(TaskComment)
        .where(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.asc())
    )
    return list(result.scalars().all())


async def get_comment(comment_id: uuid.UUID, db: AsyncSession) -> TaskComment | None:
    """ID로 댓글을 조회합니다.

    Args:
        comment_id: 댓글 UUID.
        db: 비동기 DB 세션.

    Returns:
        TaskComment 모델 또는 None.
    """
    result = await db.execute(select(TaskComment).where(TaskComment.id == comment_id))
    return result.scalar_one_or_none()


async def update_comment(
    comment_id: uuid.UUID,
    data: CommentUpdate,
    db: AsyncSession,
) -> TaskComment:
    """댓글 내용을 수정합니다.

    수정 후 새로 @mention된 사용자를 감시자로 등록합니다.

    Args:
        comment_id: 댓글 UUID.
        data: 수정할 내용.
        db: 비동기 DB 세션.

    Returns:
        수정된 TaskComment 모델.

    Raises:
        ValueError: 댓글을 찾을 수 없는 경우.
    """
    try:
        comment = await get_comment(comment_id, db)
        if not comment:
            raise ValueError("댓글을 찾을 수 없습니다.")

        comment.content = data.content
        await db.flush()
        await db.refresh(comment)

        usernames = extract_mentions(data.content)
        if usernames:
            await add_watchers(comment.task_id, usernames, db)

        return comment
    except ValueError:
        raise
    except Exception:
        logger.error(f"댓글 수정 실패: {traceback.format_exc()}")
        raise


async def delete_comment(comment_id: uuid.UUID, db: AsyncSession) -> None:
    """댓글을 삭제합니다.

    Args:
        comment_id: 댓글 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 댓글을 찾을 수 없는 경우.
    """
    try:
        comment = await get_comment(comment_id, db)
        if not comment:
            raise ValueError("댓글을 찾을 수 없습니다.")

        await db.delete(comment)
        await db.flush()
    except ValueError:
        raise
    except Exception:
        logger.error(f"댓글 삭제 실패: {traceback.format_exc()}")
        raise
