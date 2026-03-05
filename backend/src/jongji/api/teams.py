"""팀 관리 API 엔드포인트.

팀 CRUD, 멤버 관리, 역할/권한 기반 접근 제어를 제공합니다.
"""

import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user, get_db
from jongji.models.team import TeamMember
from jongji.models.user import User
from jongji.schemas.team import (
    TeamCreate,
    TeamMemberAdd,
    TeamMemberResponse,
    TeamResponse,
    TeamUpdate,
)
from jongji.services import team_service

router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


def _build_team_response(team, member_count: int) -> TeamResponse:
    """Team 모델과 멤버 수로 TeamResponse를 조립합니다.

    Args:
        team: Team ORM 모델.
        member_count: 멤버 수.

    Returns:
        TeamResponse 스키마.
    """
    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        is_archived=team.is_archived,
        created_by=team.created_by,
        member_count=member_count,
        created_at=team.created_at,
    )


async def _build_member_response(membership: TeamMember, db: AsyncSession) -> TeamMemberResponse:
    """TeamMember 모델로 TeamMemberResponse를 조립합니다.

    User 정보를 DB에서 조회하여 응답에 포함합니다.

    Args:
        membership: TeamMember ORM 모델.
        db: 비동기 DB 세션.

    Returns:
        TeamMemberResponse 스키마.
    """
    user_result = await db.execute(select(User).where(User.id == membership.user_id))
    user = user_result.scalar_one_or_none()
    return TeamMemberResponse(
        id=membership.id,
        user_id=membership.user_id,
        user_name=user.name if user else "",
        user_email=user.email if user else "",
        role=membership.role.value if hasattr(membership.role, "value") else str(membership.role),
        created_at=membership.created_at,
    )


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """현재 사용자가 속한 팀 목록을 반환합니다."""
    teams = await team_service.list_user_teams(current_user.id, db)
    result = []
    for team in teams:
        members = await team_service.get_members(team.id, db)
        result.append(_build_team_response(team, len(members)))
    return result


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """새 팀을 생성합니다. 생성자는 자동으로 리더로 등록됩니다."""
    try:
        team = await team_service.create_team(data.name, data.description, current_user.id, db)
        members = await team_service.get_members(team.id, db)
        return _build_team_response(team, len(members))
    except Exception:
        logger.error(f"팀 생성 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="팀 생성에 실패했습니다.")


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """팀 상세 정보를 반환합니다."""
    team = await team_service.get_team(team_id, db)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="팀을 찾을 수 없습니다.")
    members = await team_service.get_members(team_id, db)
    return _build_team_response(team, len(members))


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: UUID,
    data: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """팀 정보를 수정합니다. 리더 또는 관리자만 수정할 수 있습니다."""
    has_permission = await team_service.check_team_permission(current_user, team_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    try:
        team = await team_service.update_team(team_id, data, db)
        members = await team_service.get_members(team_id, db)
        return _build_team_response(team, len(members))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"팀 수정 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="팀 수정에 실패했습니다.")


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_team(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """팀을 아카이브합니다. 리더 또는 관리자만 가능하며 하위 프로젝트도 함께 아카이브됩니다."""
    has_permission = await team_service.check_team_permission(current_user, team_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    try:
        await team_service.archive_team(team_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"팀 아카이브 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="팀 아카이브에 실패했습니다.")


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
async def list_members(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """팀 멤버 목록을 반환합니다."""
    team = await team_service.get_team(team_id, db)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="팀을 찾을 수 없습니다.")

    members = await team_service.get_members(team_id, db)
    return [await _build_member_response(m, db) for m in members]


@router.post("/{team_id}/members", response_model=TeamMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    team_id: UUID,
    data: TeamMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """팀에 멤버를 추가합니다. 리더 또는 관리자만 가능합니다."""
    has_permission = await team_service.check_team_permission(current_user, team_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    try:
        membership = await team_service.add_member(team_id, data.user_id, data.role, db)
        return await _build_member_response(membership, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.error(f"팀 멤버 추가 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="멤버 추가에 실패했습니다.")


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    team_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """팀에서 멤버를 제거합니다. 리더 또는 관리자만 가능합니다."""
    has_permission = await team_service.check_team_permission(current_user, team_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")

    try:
        await team_service.remove_member(team_id, user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"팀 멤버 제거 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="멤버 제거에 실패했습니다.")
