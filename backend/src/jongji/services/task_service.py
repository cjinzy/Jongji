"""작업(Task) 서비스 모듈.

Task CRUD, 태그 추출, 담당자 프로젝트 멤버 검증 등 비즈니스 로직을 담당합니다.
"""

import uuid

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from jongji.models.enums import ProjectRole, TaskStatus, TeamRole
from jongji.models.project import Project, ProjectMember
from jongji.models.task import Task, TaskHistory, TaskLabel, TaskRelation
from jongji.models.team import TeamMember
from jongji.models.user import User
from jongji.schemas.task import TaskCreate, TaskUpdate
from jongji.services import tag_service


async def _verify_project_member(
    project_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession
) -> bool:
    """사용자가 프로젝트 멤버인지 검증합니다.

    Args:
        project_id: 프로젝트 UUID.
        user_id: 사용자 UUID.
        db: 비동기 DB 세션.

    Returns:
        멤버 여부.
    """
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def create_task(
    project_id: uuid.UUID,
    data: TaskCreate,
    creator_id: uuid.UUID,
    db: AsyncSession,
) -> Task:
    """새 작업을 생성합니다.

    SELECT FOR UPDATE로 프로젝트 행을 잠그고 task_counter를 원자적으로 증가시킵니다.

    Args:
        project_id: 프로젝트 UUID.
        data: 작업 생성 데이터.
        creator_id: 생성자 UUID.
        db: 비동기 DB 세션.

    Returns:
        생성된 Task 객체.

    Raises:
        ValueError: 프로젝트가 없거나 담당자가 프로젝트 멤버가 아닌 경우.
    """
    # SELECT FOR UPDATE로 프로젝트 잠금 + task_counter 조회
    result = await db.execute(
        select(Project).where(Project.id == project_id).with_for_update()
    )
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("프로젝트를 찾을 수 없습니다.")

    # 담당자 검증
    if data.assignee_id and not await _verify_project_member(project_id, data.assignee_id, db):
        raise ValueError("담당자가 프로젝트 멤버가 아닙니다.")

    # task_counter 증가
    new_number = project.task_counter + 1
    project.task_counter = new_number

    task = Task(
        project_id=project_id,
        number=new_number,
        title=data.title,
        description=data.description,
        status=TaskStatus.BACKLOG,
        priority=data.priority,
        creator_id=creator_id,
        assignee_id=data.assignee_id,
        start_date=data.start_date,
        due_date=data.due_date,
    )
    db.add(task)
    await db.flush()

    # 태그 동기화
    await tag_service.sync_tags(task.id, data.title, data.description, db)

    return task


async def get_task(task_id: uuid.UUID, db: AsyncSession) -> Task | None:
    """작업을 상세 조회합니다 (관계 포함).

    Args:
        task_id: 작업 UUID.
        db: 비동기 DB 세션.

    Returns:
        Task 객체 또는 None.
    """
    result = await db.execute(
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.labels).joinedload(TaskLabel.label),
            selectinload(Task.tags),
            joinedload(Task.project),
        )
    )
    return result.unique().scalar_one_or_none()


async def _check_update_permission(
    task: Task, user: User, db: AsyncSession
) -> bool:
    """작업 수정 권한을 확인합니다.

    권한 보유자: creator, assignee, project leader, team leader, admin.

    Args:
        task: 대상 작업.
        user: 요청 사용자.
        db: 비동기 DB 세션.

    Returns:
        권한 여부.
    """
    if user.is_admin:
        return True
    if task.creator_id == user.id:
        return True
    if task.assignee_id and task.assignee_id == user.id:
        return True

    # project leader 확인
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == task.project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.role == ProjectRole.LEADER,
        )
    )
    if result.scalar_one_or_none():
        return True

    # team leader 확인 (project -> team)
    project_result = await db.execute(
        select(Project.team_id).where(Project.id == task.project_id)
    )
    team_id = project_result.scalar_one_or_none()
    if team_id:
        team_result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user.id,
                TeamMember.role == TeamRole.LEADER,
            )
        )
        if team_result.scalar_one_or_none():
            return True

    return False


async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    user: User,
    db: AsyncSession,
) -> Task:
    """작업을 수정합니다.

    변경 이력을 task_history에 기록합니다.

    Args:
        task_id: 작업 UUID.
        data: 수정 데이터.
        user: 요청 사용자.
        db: 비동기 DB 세션.

    Returns:
        수정된 Task 객체.

    Raises:
        ValueError: 작업이 없거나 권한이 없는 경우.
    """
    task = await get_task(task_id, db)
    if not task:
        raise ValueError("작업을 찾을 수 없습니다.")

    if not await _check_update_permission(task, user, db):
        raise PermissionError("작업을 수정할 권한이 없습니다.")

    update_data = data.model_dump(exclude_unset=True)

    # 담당자 변경 시 멤버 검증
    if (
        "assignee_id" in update_data
        and update_data["assignee_id"] is not None
        and not await _verify_project_member(task.project_id, update_data["assignee_id"], db)
    ):
        raise ValueError("담당자가 프로젝트 멤버가 아닙니다.")

    # 변경 이력 기록 — 타입 안전한 비교 (str() 비교는 None/"None" 오탐 유발)
    for field_name, new_value in update_data.items():
        old_value = getattr(task, field_name, None)
        # UUID 등 타입이 다를 수 있으므로 str 변환 후 비교하되, None은 별도 처리
        old_str = str(old_value) if old_value is not None else None
        new_str = str(new_value) if new_value is not None else None
        if old_str != new_str:
            db.add(
                TaskHistory(
                    task_id=task.id,
                    user_id=user.id,
                    field=field_name,
                    old_value=old_str,
                    new_value=new_str,
                )
            )
            setattr(task, field_name, new_value)

    await db.flush()

    # 제목/설명 변경 시 태그 동기화
    if "title" in update_data or "description" in update_data:
        await tag_service.sync_tags(task.id, task.title, task.description, db)

    return task


async def archive_task(task_id: uuid.UUID, db: AsyncSession) -> None:
    """작업을 보관 처리합니다.

    is_archived를 True로 설정하고 관련 task_relations을 삭제합니다.

    Args:
        task_id: 작업 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 작업을 찾을 수 없는 경우.
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise ValueError("작업을 찾을 수 없습니다.")

    task.is_archived = True

    # 이 작업이 관련된 모든 relations 삭제
    await db.execute(
        delete(TaskRelation).where(
            (TaskRelation.task_id == task_id)
            | (TaskRelation.blocked_by_task_id == task_id)
        )
    )
    await db.flush()


async def list_tasks(
    project_id: uuid.UUID,
    db: AsyncSession,
    *,
    status: TaskStatus | None = None,
    assignee_id: uuid.UUID | None = None,
    priority: int | None = None,
    is_archived: bool = False,
    cursor: str | None = None,
    limit: int = 20,
) -> tuple[list[Task], str | None, bool]:
    """프로젝트 작업 목록을 조회합니다 (커서 기반 페이지네이션).

    Args:
        project_id: 프로젝트 UUID.
        db: 비동기 DB 세션.
        status: 상태 필터.
        assignee_id: 담당자 필터.
        priority: 우선순위 필터.
        is_archived: 보관 여부 필터.
        cursor: 페이지네이션 커서 (created_at|id 형식).
        limit: 페이지 크기.

    Returns:
        (작업 목록, 다음 커서, 추가 데이터 여부) 튜플.
    """
    query = (
        select(Task)
        .where(Task.project_id == project_id, Task.is_archived == is_archived)
        .options(
            selectinload(Task.labels).joinedload(TaskLabel.label),
        )
        .order_by(Task.created_at.desc(), Task.id.desc())
    )

    if status:
        query = query.where(Task.status == status)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    if priority is not None:
        query = query.where(Task.priority == priority)

    if cursor:
        parts = cursor.split("|")
        if len(parts) == 2:
            from datetime import datetime

            cursor_ts = datetime.fromisoformat(parts[0])
            cursor_id = uuid.UUID(parts[1])
            query = query.where(
                (Task.created_at < cursor_ts)
                | (
                    and_(
                        Task.created_at == cursor_ts,
                        Task.id < cursor_id,
                    )
                )
            )

    query = query.limit(limit + 1)
    result = await db.execute(query)
    tasks = list(result.unique().scalars().all())

    has_more = len(tasks) > limit
    if has_more:
        tasks = tasks[:limit]

    next_cursor = None
    if has_more and tasks:
        last = tasks[-1]
        next_cursor = f"{last.created_at.isoformat()}|{last.id}"

    return tasks, next_cursor, has_more


async def clone_task(
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Task:
    """작업을 복제합니다.

    새 번호, BACKLOG 상태로 복제하며 title, description, priority, labels를 복사합니다.
    blocked_by relations은 복사하지 않습니다.

    Args:
        task_id: 원본 작업 UUID.
        user_id: 복제 요청자 UUID.
        db: 비동기 DB 세션.

    Returns:
        복제된 Task 객체.

    Raises:
        ValueError: 원본 작업을 찾을 수 없는 경우.
    """
    original = await get_task(task_id, db)
    if not original:
        raise ValueError("작업을 찾을 수 없습니다.")

    # 프로젝트 잠금 + task_counter 증가
    result = await db.execute(
        select(Project).where(Project.id == original.project_id).with_for_update()
    )
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("프로젝트를 찾을 수 없습니다.")
    new_number = project.task_counter + 1
    project.task_counter = new_number

    cloned = Task(
        project_id=original.project_id,
        number=new_number,
        title=original.title,
        description=original.description,
        status=TaskStatus.BACKLOG,
        priority=original.priority,
        creator_id=user_id,
        assignee_id=None,
        start_date=original.start_date,
        due_date=original.due_date,
    )
    db.add(cloned)
    await db.flush()

    # labels 복사
    for task_label in original.labels:
        db.add(TaskLabel(task_id=cloned.id, label_id=task_label.label_id))

    await db.flush()
    return cloned
