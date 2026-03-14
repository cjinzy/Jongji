"""작업 템플릿 서비스 모듈.

템플릿 CRUD 및 템플릿으로 작업 생성 비즈니스 로직을 담당합니다.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.project import Project
from jongji.models.task import TaskTemplate
from jongji.schemas.task import TaskCreate
from jongji.schemas.template import TemplateCreate, TemplateUpdate
from jongji.services import task_service
from jongji.utils.safe_update import safe_update

_UPDATABLE_FIELDS: frozenset[str] = frozenset(
    {"name", "title_template", "description", "priority", "tags"}
)


async def create_template(
    project_id: uuid.UUID,
    data: TemplateCreate,
    created_by: uuid.UUID,
    db: AsyncSession,
) -> TaskTemplate:
    """새 작업 템플릿을 생성합니다.

    Args:
        project_id: 프로젝트 UUID.
        data: 템플릿 생성 데이터.
        created_by: 생성자 UUID.
        db: 비동기 DB 세션.

    Returns:
        생성된 TaskTemplate 객체.

    Raises:
        ValueError: 프로젝트가 존재하지 않는 경우.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("프로젝트를 찾을 수 없습니다.")

    template = TaskTemplate(
        project_id=project_id,
        name=data.name,
        title_template=data.title_template,
        description=data.description,
        priority=data.priority,
        tags=data.tags,
        created_by=created_by,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


async def list_templates(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> list[TaskTemplate]:
    """프로젝트의 작업 템플릿 목록을 조회합니다.

    Args:
        project_id: 프로젝트 UUID.
        db: 비동기 DB 세션.

    Returns:
        TaskTemplate 객체 목록.
    """
    result = await db.execute(
        select(TaskTemplate)
        .where(TaskTemplate.project_id == project_id)
        .order_by(TaskTemplate.created_at.asc())
    )
    return list(result.scalars().all())


async def update_template(
    template_id: uuid.UUID,
    data: TemplateUpdate,
    db: AsyncSession,
) -> TaskTemplate:
    """작업 템플릿을 수정합니다.

    Args:
        template_id: 템플릿 UUID.
        data: 수정 데이터.
        db: 비동기 DB 세션.

    Returns:
        수정된 TaskTemplate 객체.

    Raises:
        ValueError: 템플릿이 존재하지 않는 경우.
    """
    result = await db.execute(select(TaskTemplate).where(TaskTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise ValueError("템플릿을 찾을 수 없습니다.")

    update_data = data.model_dump(exclude_unset=True)
    safe_update(template, update_data, _UPDATABLE_FIELDS)

    await db.flush()
    await db.refresh(template)
    return template


async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """작업 템플릿을 삭제합니다.

    Args:
        template_id: 템플릿 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 템플릿이 존재하지 않는 경우.
    """
    result = await db.execute(select(TaskTemplate).where(TaskTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise ValueError("템플릿을 찾을 수 없습니다.")

    await db.delete(template)
    await db.flush()


async def create_task_from_template(
    template_id: uuid.UUID,
    creator_id: uuid.UUID,
    db: AsyncSession,
):
    """템플릿을 기반으로 작업을 생성합니다.

    템플릿의 title_template, description, priority, tags를 복사하여
    task_service.create_task()를 통해 작업을 생성합니다.

    Args:
        template_id: 템플릿 UUID.
        creator_id: 작업 생성자 UUID.
        db: 비동기 DB 세션.

    Returns:
        생성된 Task 객체.

    Raises:
        ValueError: 템플릿이 존재하지 않는 경우.
    """
    result = await db.execute(select(TaskTemplate).where(TaskTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise ValueError("템플릿을 찾을 수 없습니다.")

    task_data = TaskCreate(
        title=template.title_template,
        description=template.description,
        priority=template.priority,
    )
    task = await task_service.create_task(
        project_id=template.project_id,
        data=task_data,
        creator_id=creator_id,
        db=db,
    )
    # Reload with eager-loaded relationships required by TaskResponse
    return await task_service.get_task(task.id, db)
