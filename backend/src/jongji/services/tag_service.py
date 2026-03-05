"""태그 서비스 모듈.

#태그 추출, task_tags 동기화, 프로젝트별 태그 목록 조회, 태그별 작업 조회 등
비즈니스 로직을 담당합니다.
"""

import re
import traceback
import uuid

from loguru import logger
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.task import Task, TaskTag

TAG_PATTERN = re.compile(r"#([a-zA-Z가-힣0-9_-]+)")


def extract_tags(text: str) -> list[str]:
    """텍스트에서 해시태그를 추출합니다.

    Args:
        text: 태그를 포함한 텍스트.

    Returns:
        '#'를 제거한 태그 이름 목록 (중복 제거, 첫 등장 순서 유지).
    """
    return list(dict.fromkeys(TAG_PATTERN.findall(text)))


async def sync_tags(
    task_id: uuid.UUID,
    title: str | None,
    description: str | None,
    db: AsyncSession,
) -> None:
    """작업의 task_tags를 제목/설명에서 추출한 태그로 동기화합니다.

    기존 태그를 모두 삭제한 후 새 태그를 삽입합니다.

    Args:
        task_id: 작업 UUID.
        title: 작업 제목.
        description: 작업 설명.
        db: 비동기 DB 세션.
    """
    try:
        # 기존 태그 전체 삭제
        await db.execute(delete(TaskTag).where(TaskTag.task_id == task_id))

        # 제목 + 설명에서 태그 추출 (중복 제거)
        combined: list[str] = []
        if title:
            combined.extend(extract_tags(title))
        if description:
            combined.extend(extract_tags(description))

        seen: set[str] = set()
        for tag_name in combined:
            if tag_name not in seen:
                seen.add(tag_name)
                db.add(TaskTag(task_id=task_id, tag=tag_name))

        await db.flush()
    except Exception:
        logger.error(f"태그 동기화 실패 (task_id={task_id}): {traceback.format_exc()}")
        raise


async def list_tags(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict]:
    """프로젝트 내 태그 목록을 사용 횟수와 함께 반환합니다.

    Args:
        project_id: 프로젝트 UUID.
        db: 비동기 DB 세션.

    Returns:
        {'tag': str, 'count': int} 딕셔너리 목록 (count 내림차순).
    """
    try:
        stmt = (
            select(TaskTag.tag, func.count(TaskTag.id).label("count"))
            .join(Task, Task.id == TaskTag.task_id)
            .where(Task.project_id == project_id)
            .group_by(TaskTag.tag)
            .order_by(func.count(TaskTag.id).desc(), TaskTag.tag)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [{"tag": row.tag, "count": row.count} for row in rows]
    except Exception:
        logger.error(f"태그 목록 조회 실패 (project_id={project_id}): {traceback.format_exc()}")
        raise


async def get_tasks_by_tag(
    tag: str,
    project_id: uuid.UUID,
    db: AsyncSession,
) -> list[Task]:
    """특정 태그가 붙은 작업 목록을 반환합니다.

    Args:
        tag: 태그 이름 ('#' 제외).
        project_id: 프로젝트 UUID.
        db: 비동기 DB 세션.

    Returns:
        Task 목록 (생성일 내림차순).
    """
    try:
        stmt = (
            select(Task)
            .join(TaskTag, TaskTag.task_id == Task.id)
            .where(
                TaskTag.tag == tag,
                Task.project_id == project_id,
            )
            .order_by(Task.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())
    except Exception:
        logger.error(f"태그별 작업 조회 실패 (tag={tag}, project_id={project_id}): {traceback.format_exc()}")
        raise
