"""팀 초대 링크 API 엔드포인트.

초대 생성, 목록 조회, 비활성화, 토큰을 통한 팀 참여를 제공합니다.
"""

import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user, get_db
from jongji.models.user import User
from jongji.schemas.team import TeamInviteCreate, TeamInviteResponse
from jongji.services import invite_service, team_service

router = APIRouter(prefix="/api/v1/teams", tags=["invites"])


@router.get("/{team_id}/invites", response_model=list[TeamInviteResponse])
async def list_invites(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """팀의 활성 초대 링크 목록을 반환합니다."""
    has_permission = await team_service.check_team_permission(current_user, team_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
    invites = await invite_service.list_invites(team_id, db)
    return [TeamInviteResponse.model_validate(inv) for inv in invites]


@router.post("/{team_id}/invites", response_model=TeamInviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    team_id: UUID,
    data: TeamInviteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """팀 초대 링크를 생성합니다. 리더 또는 관리자만 가능합니다."""
    has_permission = await team_service.check_team_permission(current_user, team_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
    try:
        invite = await invite_service.create_invite(
            team_id=team_id,
            created_by=current_user.id,
            expires_in_days=data.expires_in_days,
            max_uses=data.max_uses,
            db=db,
        )
        await db.commit()
        return TeamInviteResponse.model_validate(invite)
    except Exception:
        logger.error(f"초대 생성 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="초대 생성에 실패했습니다.")


@router.delete("/{team_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_invite(
    team_id: UUID,
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """초대 링크를 비활성화합니다. 리더 또는 관리자만 가능합니다."""
    has_permission = await team_service.check_team_permission(current_user, team_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
    try:
        await invite_service.deactivate_invite(invite_id, team_id, db)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"초대 비활성화 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="초대 비활성화에 실패했습니다.")


@router.post("/join/{token}", status_code=status.HTTP_200_OK)
async def join_by_token(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """초대 토큰으로 팀에 참여합니다."""
    try:
        member = await invite_service.join_by_token(token, current_user.id, db)
        await db.commit()
        return {
            "team_id": str(member.team_id),
            "user_id": str(member.user_id),
            "role": member.role.value if hasattr(member.role, "value") else str(member.role),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception:
        logger.error(f"팀 참여 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="팀 참여에 실패했습니다.")
