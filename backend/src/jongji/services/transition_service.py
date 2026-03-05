"""작업 상태 전환 서비스.

상태 전환 유효성 검사, blocked_by 제약 검사, DFS 기반 사이클 감지를 담당합니다.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.enums import TaskStatus
from jongji.models.task import Task, TaskRelation

# 허용된 상태 전환 테이블
ALLOWED_TRANSITIONS: dict[TaskStatus, list[TaskStatus]] = {
    TaskStatus.BACKLOG: [TaskStatus.TODO],
    TaskStatus.TODO: [TaskStatus.PROGRESS, TaskStatus.BACKLOG],
    TaskStatus.PROGRESS: [TaskStatus.REVIEW, TaskStatus.TODO],
    TaskStatus.REVIEW: [TaskStatus.DONE, TaskStatus.PROGRESS],
    TaskStatus.DONE: [TaskStatus.CLOSED, TaskStatus.REOPEN],
    TaskStatus.REOPEN: [TaskStatus.TODO],
    TaskStatus.CLOSED: [],
}

# PROGRESS 진입 시 허용되는 blocked_by 상태
_PROGRESS_OK_STATUSES = {TaskStatus.DONE, TaskStatus.CLOSED}

# blocked_by 최대 개수
MAX_BLOCKED_BY = 10

# 사이클 감지 최대 체인 깊이
MAX_CHAIN_DEPTH = 20


def validate_transition(current: TaskStatus, target: TaskStatus) -> bool:
    """상태 전환이 허용되는지 검사합니다.

    Args:
        current: 현재 상태.
        target: 목표 상태.

    Returns:
        전환 허용 여부.
    """
    return target in ALLOWED_TRANSITIONS.get(current, [])


async def check_blocked_by(task_id: uuid.UUID, db: AsyncSession) -> list[Task]:
    """작업의 blocked_by 작업 중 미완료 상태인 것을 반환합니다.

    PROGRESS 진입 시 모든 blocked_by 작업이 DONE 또는 CLOSED여야 합니다.

    Args:
        task_id: 검사할 작업 UUID.
        db: 비동기 DB 세션.

    Returns:
        미완료 상태의 blocked_by 작업 목록.
    """
    result = await db.execute(
        select(Task)
        .join(TaskRelation, TaskRelation.blocked_by_task_id == Task.id)
        .where(TaskRelation.task_id == task_id)
    )
    blocked_by_tasks = list(result.scalars().all())
    return [t for t in blocked_by_tasks if t.status not in _PROGRESS_OK_STATUSES]


async def detect_cycle(
    task_id: uuid.UUID,
    new_blocker_id: uuid.UUID,
    db: AsyncSession,
) -> bool:
    """새 blocked_by 관계 추가 시 사이클 형성 여부를 DFS로 검사합니다.

    task_id가 new_blocker_id를 통해 자기 자신에게 도달할 수 있으면 사이클입니다.
    즉, new_blocker_id의 blocked_by 체인을 따라 task_id가 나타나면 사이클입니다.

    Args:
        task_id: 새 관계의 대상 작업 UUID (이 작업이 blocked 됨).
        new_blocker_id: 새로 추가할 blocker 작업 UUID.
        db: 비동기 DB 세션.

    Returns:
        사이클 형성 여부.
    """
    visited: set[uuid.UUID] = set()
    stack = [new_blocker_id]
    depth = 0

    while stack and depth < MAX_CHAIN_DEPTH:
        current = stack.pop()
        if current == task_id:
            return True
        if current in visited:
            continue
        visited.add(current)
        depth += 1

        # current가 blocked_by하는 작업들을 가져옴
        result = await db.execute(
            select(TaskRelation.blocked_by_task_id).where(TaskRelation.task_id == current)
        )
        parents = list(result.scalars().all())
        stack.extend(parents)

    return False


async def count_blocked_by(task_id: uuid.UUID, db: AsyncSession) -> int:
    """작업의 현재 blocked_by 관계 수를 반환합니다.

    Args:
        task_id: 작업 UUID.
        db: 비동기 DB 세션.

    Returns:
        blocked_by 관계 수.
    """
    result = await db.execute(
        select(func.count()).where(TaskRelation.task_id == task_id)
    )
    return result.scalar_one()
