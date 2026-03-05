"""팀 관리 서비스 레이어.

팀 CRUD, 멤버 관리, 역할/권한 검증 등의 비즈니스 로직을 처리합니다.
"""

import traceback
import uuid

from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.enums import TeamRole
from jongji.models.project import Project
from jongji.models.team import Team, TeamMember
from jongji.models.user import User
from jongji.schemas.team import TeamUpdate
from jongji.utils.slug import generate_slug


async def _unique_team_slug(name: str, db: AsyncSession) -> str:
    """팀 이름으로부터 유니크한 slug를 생성합니다.

    동일 slug가 존재할 경우 -1, -2 등 숫자 접미사를 추가합니다.

    Args:
        name: 팀 이름.
        db: 비동기 DB 세션.

    Returns:
        유니크한 slug 문자열.
    """
    base_slug = generate_slug(name)
    slug = base_slug
    suffix = 0
    while True:
        result = await db.execute(select(Team).where(Team.slug == slug))
        if result.scalar_one_or_none() is None:
            return slug
        suffix += 1
        slug = f"{base_slug}-{suffix}"


async def get_team_by_slug(slug: str, db: AsyncSession) -> Team | None:
    """slug로 팀을 조회합니다.

    Args:
        slug: 팀 slug.
        db: 비동기 DB 세션.

    Returns:
        Team 모델 또는 None.
    """
    result = await db.execute(select(Team).where(Team.slug == slug))
    return result.scalar_one_or_none()


async def create_team(name: str, description: str | None, creator_id: uuid.UUID, db: AsyncSession) -> Team:
    """팀을 생성하고 생성자를 리더로 등록합니다.

    Args:
        name: 팀 이름.
        description: 팀 설명.
        creator_id: 생성자 사용자 UUID.
        db: 비동기 DB 세션.

    Returns:
        생성된 Team 모델.
    """
    try:
        slug = await _unique_team_slug(name, db)
        team = Team(name=name, slug=slug, description=description, created_by=creator_id)
        db.add(team)
        await db.flush()

        membership = TeamMember(
            team_id=team.id,
            user_id=creator_id,
            role=TeamRole.LEADER,
        )
        db.add(membership)
        await db.flush()
        await db.refresh(team)
        return team
    except Exception:
        logger.error(f"팀 생성 실패: {traceback.format_exc()}")
        raise


async def get_team(team_id: uuid.UUID, db: AsyncSession) -> Team | None:
    """ID로 팀을 조회합니다.

    Args:
        team_id: 팀 UUID.
        db: 비동기 DB 세션.

    Returns:
        Team 모델 또는 None.
    """
    result = await db.execute(select(Team).where(Team.id == team_id))
    return result.scalar_one_or_none()


async def update_team(team_id: uuid.UUID, data: TeamUpdate, db: AsyncSession) -> Team:
    """팀 정보를 수정합니다.

    Args:
        team_id: 팀 UUID.
        data: 수정할 필드 데이터.
        db: 비동기 DB 세션.

    Returns:
        수정된 Team 모델.

    Raises:
        ValueError: 팀을 찾을 수 없는 경우.
    """
    try:
        team = await get_team(team_id, db)
        if not team:
            raise ValueError("팀을 찾을 수 없습니다.")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(team, field, value)

        await db.flush()
        await db.refresh(team)
        return team
    except ValueError:
        raise
    except Exception:
        logger.error(f"팀 수정 실패: {traceback.format_exc()}")
        raise


async def archive_team(team_id: uuid.UUID, db: AsyncSession) -> None:
    """팀을 아카이브하고 하위 프로젝트를 캐스케이드 아카이브합니다.

    Args:
        team_id: 팀 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 팀을 찾을 수 없는 경우.
    """
    try:
        team = await get_team(team_id, db)
        if not team:
            raise ValueError("팀을 찾을 수 없습니다.")

        # 하위 프로젝트 캐스케이드 아카이브
        await db.execute(
            update(Project).where(Project.team_id == team_id).values(is_archived=True)
        )

        team.is_archived = True
        await db.flush()
    except ValueError:
        raise
    except Exception:
        logger.error(f"팀 아카이브 실패: {traceback.format_exc()}")
        raise


async def list_user_teams_with_counts(
    user_id: uuid.UUID, db: AsyncSession
) -> list[tuple[Team, int]]:
    """사용자가 속한 활성 팀 목록을 멤버 수와 함께 반환합니다.

    N+1 쿼리를 방지하기 위해 멤버 수를 서브쿼리로 함께 조회합니다.

    Args:
        user_id: 사용자 UUID.
        db: 비동기 DB 세션.

    Returns:
        (Team, member_count) 튜플 목록 (아카이브된 팀 제외).
    """
    member_count_sq = (
        select(func.count(TeamMember.id))
        .where(TeamMember.team_id == Team.id)
        .correlate(Team)
        .scalar_subquery()
        .label("member_count")
    )
    stmt = (
        select(Team, member_count_sq)
        .join(TeamMember, TeamMember.team_id == Team.id)
        .where(
            TeamMember.user_id == user_id,
            Team.is_archived.is_(False),
        )
    )
    result = await db.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def add_member(
    team_id: uuid.UUID, user_id: uuid.UUID, role: str, db: AsyncSession
) -> TeamMember:
    """팀에 멤버를 추가합니다.

    Args:
        team_id: 팀 UUID.
        user_id: 추가할 사용자 UUID.
        role: 역할 ('leader' 또는 'member').
        db: 비동기 DB 세션.

    Returns:
        생성된 TeamMember 모델.

    Raises:
        ValueError: 팀 또는 사용자를 찾을 수 없는 경우, 이미 멤버인 경우.
    """
    try:
        team = await get_team(team_id, db)
        if not team:
            raise ValueError("팀을 찾을 수 없습니다.")

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("사용자를 찾을 수 없습니다.")

        existing = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("이미 팀 멤버입니다.")

        team_role = TeamRole.LEADER if role == "leader" else TeamRole.MEMBER
        membership = TeamMember(team_id=team_id, user_id=user_id, role=team_role)
        db.add(membership)
        await db.flush()
        await db.refresh(membership)
        return membership
    except ValueError:
        raise
    except Exception:
        logger.error(f"팀 멤버 추가 실패: {traceback.format_exc()}")
        raise


async def remove_member(team_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> None:
    """팀에서 멤버를 제거합니다.

    Args:
        team_id: 팀 UUID.
        user_id: 제거할 사용자 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 멤버를 찾을 수 없는 경우.
    """
    try:
        result = await db.execute(
            select(TeamMember).where(
                TeamMember.team_id == team_id, TeamMember.user_id == user_id
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise ValueError("팀 멤버를 찾을 수 없습니다.")

        await db.delete(membership)
        await db.flush()
    except ValueError:
        raise
    except Exception:
        logger.error(f"팀 멤버 제거 실패: {traceback.format_exc()}")
        raise


async def get_members(team_id: uuid.UUID, db: AsyncSession) -> list[TeamMember]:
    """팀 멤버 목록을 반환합니다.

    Args:
        team_id: 팀 UUID.
        db: 비동기 DB 세션.

    Returns:
        TeamMember 목록.
    """
    result = await db.execute(
        select(TeamMember).where(TeamMember.team_id == team_id)
    )
    return list(result.scalars().all())


async def check_team_permission(user: User, team_id: uuid.UUID, db: AsyncSession) -> bool:
    """사용자가 팀 리더 또는 관리자인지 확인합니다.

    Args:
        user: 현재 사용자.
        team_id: 팀 UUID.
        db: 비동기 DB 세션.

    Returns:
        권한 보유 여부.
    """
    if user.is_admin:
        return True

    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id,
            TeamMember.role == TeamRole.LEADER,
        )
    )
    return result.scalar_one_or_none() is not None
