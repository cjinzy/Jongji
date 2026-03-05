"""프로젝트 관리 서비스 레이어.

Project/ProjectMember CRUD 및 권한 검증 비즈니스 로직을 처리합니다.
"""

import traceback
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.enums import ProjectRole
from jongji.models.project import Project, ProjectMember
from jongji.models.team import Team, TeamMember
from jongji.models.user import User
from jongji.schemas.project import ProjectCreate, ProjectMemberAdd, ProjectUpdate
from jongji.utils.slug import generate_slug


async def _unique_project_slug(name: str, team_id: uuid.UUID, db: AsyncSession) -> str:
    """팀 범위 내에서 유니크한 프로젝트 slug를 생성합니다.

    동일 slug가 해당 팀 내에 존재할 경우 -1, -2 등 숫자 접미사를 추가합니다.

    Args:
        name: 프로젝트 이름.
        team_id: 소속 팀 UUID.
        db: 비동기 DB 세션.

    Returns:
        팀 내 유니크한 slug 문자열.
    """
    base_slug = generate_slug(name)
    slug = base_slug
    suffix = 0
    while True:
        result = await db.execute(
            select(Project).where(Project.team_id == team_id, Project.slug == slug)
        )
        if result.scalar_one_or_none() is None:
            return slug
        suffix += 1
        slug = f"{base_slug}-{suffix}"


async def get_project_by_slug(team_slug: str, project_slug: str, db: AsyncSession) -> Project | None:
    """team_slug와 project_slug로 프로젝트를 조회합니다.

    Args:
        team_slug: 팀 slug.
        project_slug: 프로젝트 slug.
        db: 비동기 DB 세션.

    Returns:
        Project 모델 또는 None.
    """
    result = await db.execute(
        select(Project)
        .join(Team, Team.id == Project.team_id)
        .where(Team.slug == team_slug, Project.slug == project_slug)
    )
    return result.scalar_one_or_none()


async def create_project(data: ProjectCreate, owner_id: uuid.UUID, db: AsyncSession) -> Project:
    """새 프로젝트를 생성하고 소유자를 리더로 등록합니다.

    key는 아카이브된 프로젝트를 포함하여 전역 UNIQUE이므로 중복 시 ValueError를 발생시킵니다.

    Args:
        data: 프로젝트 생성 데이터.
        owner_id: 소유자(생성자) UUID.
        db: 비동기 DB 세션.

    Returns:
        생성된 Project 모델.

    Raises:
        ValueError: key가 이미 사용 중인 경우.
    """
    try:
        # key 중복 검사 (아카이브 포함 영구 점유)
        existing = await db.execute(select(Project).where(Project.key == data.key))
        if existing.scalar_one_or_none():
            raise ValueError(f"프로젝트 key '{data.key}'는 이미 사용 중입니다.")

        slug = await _unique_project_slug(data.name, data.team_id, db)
        project = Project(
            team_id=data.team_id,
            name=data.name,
            slug=slug,
            key=data.key,
            description=data.description,
            is_private=data.is_private,
            owner_id=owner_id,
        )
        db.add(project)
        await db.flush()

        # 소유자를 프로젝트 리더로 자동 추가
        member = ProjectMember(
            project_id=project.id,
            user_id=owner_id,
            role=ProjectRole.LEADER,
        )
        db.add(member)
        await db.flush()
        await db.refresh(project)
        return project
    except ValueError:
        raise
    except Exception:
        logger.error(f"프로젝트 생성 실패: {traceback.format_exc()}")
        raise


async def get_project(project_id: uuid.UUID, db: AsyncSession) -> Project:
    """프로젝트를 ID로 조회합니다.

    Args:
        project_id: 프로젝트 UUID.
        db: 비동기 DB 세션.

    Returns:
        Project 모델.

    Raises:
        ValueError: 프로젝트를 찾을 수 없는 경우.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("프로젝트를 찾을 수 없습니다.")
    return project


async def update_project(project_id: uuid.UUID, data: ProjectUpdate, db: AsyncSession) -> Project:
    """프로젝트 정보를 수정합니다.

    Args:
        project_id: 수정할 프로젝트 UUID.
        data: 수정할 필드 데이터.
        db: 비동기 DB 세션.

    Returns:
        업데이트된 Project 모델.

    Raises:
        ValueError: 프로젝트를 찾을 수 없는 경우.
    """
    project = await get_project(project_id, db)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    await db.flush()
    await db.refresh(project)
    return project


async def archive_project(project_id: uuid.UUID, db: AsyncSession) -> None:
    """프로젝트를 아카이브 처리합니다.

    아카이브 후에도 key는 DB에서 유지되어 영구 점유됩니다.

    Args:
        project_id: 아카이브할 프로젝트 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 프로젝트를 찾을 수 없는 경우.
    """
    project = await get_project(project_id, db)
    project.is_archived = True
    await db.flush()


async def list_projects(
    team_id: uuid.UUID, db: AsyncSession, *, limit: int = 50, offset: int = 0
) -> list[Project]:
    """팀의 활성(비아카이브) 프로젝트 목록을 반환합니다.

    Args:
        team_id: 팀 UUID.
        db: 비동기 DB 세션.
        limit: 최대 반환 개수.
        offset: 건너뛸 개수.

    Returns:
        활성 Project 목록.
    """
    result = await db.execute(
        select(Project)
        .where(
            Project.team_id == team_id,
            Project.is_archived.is_(False),
        )
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_members(project_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    """프로젝트 멤버 목록을 사용자 정보와 함께 반환합니다.

    Args:
        project_id: 프로젝트 UUID.
        db: 비동기 DB 세션.

    Returns:
        멤버 정보 딕셔너리 목록.
    """
    from jongji.models.user import User

    result = await db.execute(
        select(ProjectMember, User)
        .join(User, ProjectMember.user_id == User.id)
        .where(ProjectMember.project_id == project_id)
    )
    rows = result.all()
    members = []
    for pm, user in rows:
        members.append({
            "id": pm.id,
            "user_id": pm.user_id,
            "user_name": user.name,
            "user_email": user.email,
            "role": pm.role,
            "min_alert_priority": pm.min_alert_priority,
            "created_at": pm.created_at,
        })
    return members


async def add_member(
    project_id: uuid.UUID, data: ProjectMemberAdd, db: AsyncSession
) -> dict:
    """프로젝트에 멤버를 추가합니다.

    추가하려는 사용자가 해당 프로젝트의 팀 멤버여야 합니다.

    Args:
        project_id: 프로젝트 UUID.
        data: 멤버 추가 데이터.
        db: 비동기 DB 세션.

    Returns:
        추가된 멤버 정보 딕셔너리.

    Raises:
        ValueError: 팀 멤버가 아니거나 이미 프로젝트 멤버인 경우.
    """
    from jongji.models.user import User

    try:
        project = await get_project(project_id, db)

        # 해당 사용자가 팀 멤버인지 검증
        team_check = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == project.team_id,
                TeamMember.user_id == data.user_id,
            )
        )
        if not team_check.scalar_one_or_none():
            raise ValueError("해당 사용자는 팀 멤버가 아닙니다.")

        # 이미 프로젝트 멤버인지 검증
        existing = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == data.user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("이미 프로젝트 멤버입니다.")

        try:
            role = ProjectRole(data.role)
        except ValueError:
            role = ProjectRole.MEMBER
        pm = ProjectMember(
            project_id=project_id,
            user_id=data.user_id,
            role=role,
        )
        db.add(pm)
        await db.flush()
        await db.refresh(pm)

        user_result = await db.execute(select(User).where(User.id == data.user_id))
        user = user_result.scalar_one()
        return {
            "id": pm.id,
            "user_id": pm.user_id,
            "user_name": user.name,
            "user_email": user.email,
            "role": pm.role,
            "min_alert_priority": pm.min_alert_priority,
            "created_at": pm.created_at,
        }
    except ValueError:
        raise
    except Exception:
        logger.error(f"멤버 추가 실패: {traceback.format_exc()}")
        raise


async def remove_member(project_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    """프로젝트에서 멤버를 제거합니다.

    Args:
        project_id: 프로젝트 UUID.
        user_id: 제거할 사용자 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 해당 멤버를 찾을 수 없는 경우.
    """
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    pm = result.scalar_one_or_none()
    if not pm:
        raise ValueError("프로젝트 멤버를 찾을 수 없습니다.")
    await db.delete(pm)
    await db.flush()


async def check_project_permission(user: User, project_id: uuid.UUID, db: AsyncSession) -> bool:
    """사용자가 프로젝트 수정 권한(소유자/리더/관리자)을 가지는지 확인합니다.

    Args:
        user: 현재 사용자.
        project_id: 프로젝트 UUID.
        db: 비동기 DB 세션.

    Returns:
        권한 보유 여부.
    """
    if user.is_admin:
        return True

    project = await get_project(project_id, db)
    if project.owner_id == user.id:
        return True

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.role == ProjectRole.LEADER,
        )
    )
    return result.scalar_one_or_none() is not None
