"""Task API 엔드포인트.

작업 CRUD, 클론, 필터 기반 목록 조회를 제공합니다.
"""

import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user
from jongji.database import get_db
from jongji.models.enums import TaskStatus
from jongji.models.task import TaskHistory, TaskRelation
from jongji.models.user import User
from jongji.schemas.common import CursorPage
from jongji.schemas.task import (
    TaskCloneResponse,
    TaskCreate,
    TaskLabelResponse,
    TaskRelationCreate,
    TaskRelationResponse,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from jongji.services import task_service
from jongji.services.transition_service import (
    MAX_BLOCKED_BY,
    check_blocked_by,
    count_blocked_by,
    detect_cycle,
    validate_transition,
)

router = APIRouter(tags=["tasks"])


def _task_to_response(task) -> TaskResponse:
    """Task 모델을 TaskResponse로 변환합니다.

    Args:
        task: Task SQLAlchemy 모델.

    Returns:
        TaskResponse 스키마.
    """
    labels = []
    for tl in task.labels:
        label = getattr(tl, "label", None)
        labels.append(
            TaskLabelResponse(
                label_id=tl.label_id,
                name=label.name if label else None,
                color=label.color if label else None,
            )
        )

    project_key = ""
    if hasattr(task, "project") and task.project:
        project_key = task.project.key

    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        number=task.number,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        creator_id=task.creator_id,
        assignee_id=task.assignee_id,
        start_date=task.start_date,
        due_date=task.due_date,
        is_archived=task.is_archived,
        created_at=task.created_at,
        updated_at=task.updated_at,
        labels=labels,
        project_key=project_key,
    )


@router.get("/api/v1/projects/{project_id}/tasks")
async def list_tasks(
    project_id: uuid.UUID,
    status_filter: TaskStatus | None = Query(None, alias="status"),
    assignee_id: uuid.UUID | None = Query(None),
    priority: int | None = Query(None),
    is_archived: bool = Query(False),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CursorPage[TaskResponse]:
    """프로젝트 작업 목록을 조회합니다.

    Args:
        project_id: 프로젝트 UUID.
        status_filter: 상태 필터.
        assignee_id: 담당자 필터.
        priority: 우선순위 필터.
        is_archived: 보관 여부 필터.
        cursor: 페이지네이션 커서.
        limit: 페이지 크기 (1-100).
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        CursorPage[TaskResponse]: 페이지네이션된 작업 목록.
    """
    tasks, next_cursor, has_more = await task_service.list_tasks(
        project_id,
        db,
        status=status_filter,
        assignee_id=assignee_id,
        priority=priority,
        is_archived=is_archived,
        cursor=cursor,
        limit=limit,
    )
    return CursorPage(
        items=[_task_to_response(t) for t in tasks],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.post("/api/v1/projects/{project_id}/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: uuid.UUID,
    data: TaskCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """새 작업을 생성합니다.

    Args:
        project_id: 프로젝트 UUID.
        data: 작업 생성 데이터.
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        TaskResponse: 생성된 작업.

    Raises:
        HTTPException: 프로젝트 미존재 또는 담당자 검증 실패 시.
    """
    try:
        task = await task_service.create_task(project_id, data, user.id, db)
        await db.commit()
        full_task = await task_service.get_task(task.id, db)
        return _task_to_response(full_task)
    except ValueError as e:
        logger.warning(f"작업 생성 실패: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/api/v1/tasks/{task_id}")
async def get_task(
    task_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """작업 상세를 조회합니다.

    Args:
        task_id: 작업 UUID.
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        TaskResponse: 작업 상세.

    Raises:
        HTTPException: 작업 미존재 시 404.
    """
    task = await task_service.get_task(task_id, db)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")
    return _task_to_response(task)


@router.put("/api/v1/tasks/{task_id}")
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """작업을 수정합니다.

    Args:
        task_id: 작업 UUID.
        data: 수정 데이터.
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        TaskResponse: 수정된 작업.

    Raises:
        HTTPException: 작업 미존재, 권한 없음 시.
    """
    try:
        task = await task_service.update_task(task_id, data, user, db)
        await db.commit()
        full_task = await task_service.get_task(task.id, db)
        return _task_to_response(full_task)
    except ValueError as e:
        logger.warning(f"작업 수정 실패: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/api/v1/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """작업을 보관 처리합니다.

    Args:
        task_id: 작업 UUID.
        user: 인증된 사용자.
        db: DB 세션.

    Raises:
        HTTPException: 작업 미존재 또는 권한 없음 시.
    """
    task = await task_service.get_task(task_id, db)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")

    from jongji.services.task_service import _check_update_permission
    if not await _check_update_permission(task, user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="작업을 보관할 권한이 없습니다.")

    try:
        await task_service.archive_task(task_id, db)
        await db.commit()
    except ValueError as e:
        logger.warning(f"작업 보관 실패: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/api/v1/tasks/{task_id}/clone", status_code=status.HTTP_201_CREATED)
async def clone_task(
    task_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskCloneResponse:
    """작업을 복제합니다.

    Args:
        task_id: 원본 작업 UUID.
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        TaskCloneResponse: 복제된 작업.

    Raises:
        HTTPException: 원본 작업 미존재 시.
    """
    try:
        cloned = await task_service.clone_task(task_id, user.id, db)
        await db.commit()
        full_task = await task_service.get_task(cloned.id, db)
        resp = _task_to_response(full_task)
        return TaskCloneResponse(**resp.model_dump())
    except ValueError as e:
        logger.warning(f"작업 복제 실패: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/api/v1/tasks/{task_id}/status")
async def update_task_status(
    task_id: uuid.UUID,
    data: TaskStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """작업 상태를 전환합니다.

    허용된 전환 테이블에 따라 상태를 변경하며, PROGRESS 진입 시
    blocked_by 작업이 모두 DONE 또는 CLOSED인지 검사합니다.

    Args:
        task_id: 작업 UUID.
        data: 목표 상태.
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        TaskResponse: 변경된 작업.

    Raises:
        HTTPException 404: 작업 미존재.
        HTTPException 403: 권한 없음.
        HTTPException 422: 허용되지 않는 전환 또는 blocked_by 미완료.
    """
    task = await task_service.get_task(task_id, db)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")

    # 권한 검사
    from jongji.services.task_service import _check_update_permission
    if not await _check_update_permission(task, user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="상태를 변경할 권한이 없습니다.")

    # 전환 유효성 검사
    if not validate_transition(task.status, data.status):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{task.status} -> {data.status} 전환은 허용되지 않습니다.",
        )

    # PROGRESS 진입 시 blocked_by 검사
    if data.status == TaskStatus.PROGRESS:
        unfinished = await check_blocked_by(task_id, db)
        if unfinished:
            ids = [str(t.id) for t in unfinished]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"blocked_by 작업이 완료되지 않았습니다: {ids}",
            )

    try:
        old_status = task.status
        task.status = data.status
        # 상태 변경 이력 기록
        db.add(
            TaskHistory(
                task_id=task.id,
                user_id=user.id,
                field="status",
                old_value=old_status.value if hasattr(old_status, "value") else str(old_status),
                new_value=data.status.value if hasattr(data.status, "value") else str(data.status),
            )
        )
        await db.flush()
        await db.commit()
        full_task = await task_service.get_task(task.id, db)
        logger.info(f"작업 {task_id} 상태 전환: {old_status} -> {data.status}")
        return _task_to_response(full_task)
    except Exception:
        logger.error(f"작업 상태 전환 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="상태 전환에 실패했습니다.",
        )


@router.post("/api/v1/tasks/{task_id}/relations", status_code=status.HTTP_201_CREATED)
async def add_task_relation(
    task_id: uuid.UUID,
    data: TaskRelationCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskRelationResponse:
    """작업에 blocked_by 관계를 추가합니다.

    자기 참조, 사이클, 최대 10개 제한을 검사합니다.

    Args:
        task_id: 대상 작업 UUID.
        data: 추가할 blocker 작업 UUID.
        user: 인증된 사용자.
        db: DB 세션.

    Returns:
        TaskRelationResponse: 생성된 관계.

    Raises:
        HTTPException 404: 작업 미존재.
        HTTPException 422: 자기 참조, 사이클, 개수 초과.
    """
    task = await task_service.get_task(task_id, db)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="작업을 찾을 수 없습니다.")

    # 자기 참조 검사
    if task_id == data.blocked_by_task_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="자기 자신을 blocked_by로 설정할 수 없습니다.",
        )

    # blocker 작업 존재 여부 확인
    from jongji.models.task import Task as TaskModel
    blocker_res = await db.execute(select(TaskModel).where(TaskModel.id == data.blocked_by_task_id))
    blocker = blocker_res.scalar_one_or_none()
    if not blocker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="blocker 작업을 찾을 수 없습니다.")

    # 최대 10개 제한
    current_count = await count_blocked_by(task_id, db)
    if current_count >= MAX_BLOCKED_BY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"blocked_by는 최대 {MAX_BLOCKED_BY}개까지 설정할 수 있습니다.",
        )

    # 사이클 감지
    has_cycle = await detect_cycle(task_id, data.blocked_by_task_id, db)
    if has_cycle:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="순환 의존성이 감지되었습니다.",
        )

    try:
        relation = TaskRelation(task_id=task_id, blocked_by_task_id=data.blocked_by_task_id)
        db.add(relation)
        await db.flush()
        await db.commit()
        await db.refresh(relation)
        return TaskRelationResponse.model_validate(relation)
    except Exception:
        logger.error(f"관계 추가 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="관계 추가에 실패했습니다.",
        )


@router.delete("/api/v1/tasks/{task_id}/relations/{blocker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task_relation(
    task_id: uuid.UUID,
    blocker_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """작업의 blocked_by 관계를 삭제합니다.

    Args:
        task_id: 대상 작업 UUID.
        blocker_id: 제거할 blocker 작업 UUID.
        user: 인증된 사용자.
        db: DB 세션.

    Raises:
        HTTPException 404: 관계 미존재.
    """
    result = await db.execute(
        select(TaskRelation).where(
            TaskRelation.task_id == task_id,
            TaskRelation.blocked_by_task_id == blocker_id,
        )
    )
    relation = result.scalar_one_or_none()
    if not relation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관계를 찾을 수 없습니다.")

    try:
        await db.execute(
            delete(TaskRelation).where(
                TaskRelation.task_id == task_id,
                TaskRelation.blocked_by_task_id == blocker_id,
            )
        )
        await db.commit()
    except Exception:
        logger.error(f"관계 삭제 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="관계 삭제에 실패했습니다.",
        )
