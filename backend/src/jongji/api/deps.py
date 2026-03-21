"""FastAPI 공통 dependency 모듈.

각 API 엔드포인트에서 재사용할 dependency 함수들을 정의합니다.
인증 관련 dependency는 worker-5가 구현 완료 시 교체될 수 있습니다.
"""

import traceback
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.config import settings
from jongji.database import get_db
from jongji.models.project import Project
from jongji.models.team import TeamMember
from jongji.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """현재 인증된 사용자를 반환합니다.

    Bearer 토큰에서 사용자 ID를 추출하고 DB에서 조회합니다.
    AUTH_DISABLED=true인 경우 첫 번째 관리자 사용자를 자동 반환합니다.

    Args:
        credentials: HTTP Bearer 인증 정보.
        db: 비동기 DB 세션.

    Returns:
        인증된 User 모델.

    Raises:
        HTTPException: 인증 실패 시 401 또는 403.
    """
    if settings.AUTH_DISABLED:
        result = await db.execute(
            select(User).where(User.is_admin.is_(True), User.is_active.is_(True)).limit(1)
        )
        user = result.scalar_one_or_none()
        if user:
            return user
        logger.warning("AUTH_DISABLED이지만 활성 관리자 사용자가 없습니다. 먼저 setup을 실행하세요.")

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")

    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="잘못된 토큰입니다.")
    except JWTError:
        logger.warning(f"JWT 디코딩 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="잘못된 토큰입니다.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다.")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """관리자 권한을 검증합니다.

    Args:
        user: 현재 인증된 사용자.

    Returns:
        관리자인 User 모델.

    Raises:
        HTTPException: 관리자가 아닌 경우 403.
    """
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return user


async def require_team_member(
    team_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TeamMember | None:
    """팀 멤버십을 검증하고 TeamMember 객체를 반환합니다.

    team_id로 팀 존재 여부를 먼저 확인하고, 멤버십을 검증합니다.
    관리자(is_admin)는 팀 멤버가 아니어도 접근 가능합니다.

    Args:
        team_id: 검증할 팀 UUID.
        user: 현재 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        TeamMember: 해당 사용자의 팀 멤버십 객체 (admin의 경우 None 가능성 있음).

    Raises:
        HTTPException: 팀 미존재 시 404, 팀 멤버가 아닌 경우 403.
    """
    from jongji.models.team import Team

    # 팀 존재 여부 먼저 확인
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    if not team_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="팀을 찾을 수 없습니다.",
        )

    result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user.id,
        )
    )
    membership = result.scalar_one_or_none()

    # 관리자는 팀 멤버가 아니어도 접근 가능
    if not membership and user.is_admin:
        return None

    if not membership:
        logger.warning(
            f"IDOR 차단: user={user.id} 가 team={team_id} 에 접근 시도"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 리소스에 대한 접근 권한이 없습니다.",
        )
    return membership


async def require_project_access(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """프로젝트 접근 권한을 검증하고 현재 사용자를 반환합니다.

    project_id로 프로젝트를 조회해 team_id를 획득한 뒤,
    TeamMember 테이블에서 해당 팀의 멤버인지 확인합니다.
    멤버가 아닌 경우 403 Forbidden을 반환합니다.

    Args:
        project_id: 검증할 프로젝트 UUID.
        user: 현재 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        User: 인증된 현재 사용자.

    Raises:
        HTTPException: 프로젝트 미존재 시 404, 팀 멤버가 아닌 경우 403.
    """
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )

    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == project.team_id,
            TeamMember.user_id == user.id,
        )
    )
    membership = member_result.scalar_one_or_none()

    # 관리자는 팀 멤버가 아니어도 접근 가능
    if not membership and user.is_admin:
        return user

    if not membership:
        logger.warning(
            f"IDOR 차단: user={user.id} 가 project={project_id} (team={project.team_id}) 에 접근 시도"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 리소스에 대한 접근 권한이 없습니다.",
        )
    return user


async def require_task_access(
    task_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """업무 접근 권한을 검증하고 현재 사용자를 반환합니다.

    task_id로 업무를 조회해 project_id를 획득하고,
    해당 프로젝트의 팀 멤버인지 확인합니다.

    Args:
        task_id: 검증할 업무 UUID.
        user: 현재 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        User: 인증된 현재 사용자.

    Raises:
        HTTPException: 업무 미존재 시 404, 팀 멤버가 아닌 경우 403.
    """
    from jongji.models.task import Task

    task_result = await db.execute(select(Task).where(Task.id == task_id))
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="업무를 찾을 수 없습니다.",
        )

    proj_result = await db.execute(select(Project).where(Project.id == task.project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )

    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == project.team_id,
            TeamMember.user_id == user.id,
        )
    )
    membership = member_result.scalar_one_or_none()

    if not membership and user.is_admin:
        return user

    if not membership:
        logger.warning(
            f"IDOR 차단: user={user.id} 가 task={task_id} (project={task.project_id}) 에 접근 시도"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 리소스에 대한 접근 권한이 없습니다.",
        )
    return user


async def require_label_access(
    label_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """라벨 접근 권한을 검증하고 현재 사용자를 반환합니다.

    label_id로 라벨을 조회해 project_id를 획득하고,
    해당 프로젝트의 팀 멤버인지 확인합니다.

    Args:
        label_id: 검증할 라벨 UUID.
        user: 현재 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        User: 인증된 현재 사용자.

    Raises:
        HTTPException: 라벨 미존재 시 404, 팀 멤버가 아닌 경우 403.
    """
    from jongji.models.label import Label

    label_result = await db.execute(select(Label).where(Label.id == label_id))
    label = label_result.scalar_one_or_none()
    if not label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="라벨을 찾을 수 없습니다.",
        )

    proj_result = await db.execute(select(Project).where(Project.id == label.project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )

    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == project.team_id,
            TeamMember.user_id == user.id,
        )
    )
    membership = member_result.scalar_one_or_none()

    if not membership and user.is_admin:
        return user

    if not membership:
        logger.warning(
            f"IDOR 차단: user={user.id} 가 label={label_id} (project={label.project_id}) 에 접근 시도"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 리소스에 대한 접근 권한이 없습니다.",
        )
    return user


async def require_template_access(
    template_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """템플릿 접근 권한을 검증하고 현재 사용자를 반환합니다.

    template_id로 템플릿을 조회해 project_id를 획득하고,
    해당 프로젝트의 팀 멤버인지 확인합니다.

    Args:
        template_id: 검증할 템플릿 UUID.
        user: 현재 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        User: 인증된 현재 사용자.

    Raises:
        HTTPException: 템플릿 미존재 시 404, 팀 멤버가 아닌 경우 403.
    """
    from jongji.models.task import TaskTemplate

    template_result = await db.execute(select(TaskTemplate).where(TaskTemplate.id == template_id))
    template = template_result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="템플릿을 찾을 수 없습니다.",
        )

    proj_result = await db.execute(select(Project).where(Project.id == template.project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다.",
        )

    member_result = await db.execute(
        select(TeamMember).where(
            TeamMember.team_id == project.team_id,
            TeamMember.user_id == user.id,
        )
    )
    membership = member_result.scalar_one_or_none()

    if not membership and user.is_admin:
        return user

    if not membership:
        logger.warning(
            f"IDOR 차단: user={user.id} 가 template={template_id} (project={template.project_id}) 에 접근 시도"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 리소스에 대한 접근 권한이 없습니다.",
        )
    return user


__all__ = [
    "get_db", "get_current_user", "require_admin",
    "require_team_member", "require_project_access",
    "require_task_access", "require_label_access",
    "require_template_access",
]
