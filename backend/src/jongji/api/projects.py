"""프로젝트 관리 API 엔드포인트.

프로젝트 CRUD, 멤버 관리, 아카이브 기능을 제공합니다.
"""

import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user, get_db
from jongji.models.user import User
from jongji.schemas.project import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)
from jongji.services import project_service

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    team_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """팀에 속한 활성 프로젝트 목록을 반환합니다."""
    projects = await project_service.list_projects(team_id, db)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """새 프로젝트를 생성합니다. 생성자는 자동으로 리더로 등록됩니다."""
    try:
        project = await project_service.create_project(data, current_user.id, db)
        await db.commit()
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        logger.error(f"프로젝트 생성 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="프로젝트 생성에 실패했습니다.")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 상세 정보를 반환합니다."""
    try:
        project = await project_service.get_project(project_id, db)
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 정보를 수정합니다. 소유자/리더/관리자만 수정할 수 있습니다."""
    has_permission = await project_service.check_project_permission(current_user, project_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
    try:
        project = await project_service.update_project(project_id, data, db)
        await db.commit()
        return ProjectResponse.model_validate(project)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"프로젝트 수정 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="프로젝트 수정에 실패했습니다.")


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트를 아카이브합니다. 소유자/리더/관리자만 가능합니다."""
    has_permission = await project_service.check_project_permission(current_user, project_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
    try:
        await project_service.archive_project(project_id, db)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"프로젝트 아카이브 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="프로젝트 아카이브에 실패했습니다.")


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
async def list_members(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 멤버 목록을 반환합니다."""
    try:
        await project_service.get_project(project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    members = await project_service.get_members(project_id, db)
    return [ProjectMemberResponse(**m) for m in members]


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    project_id: UUID,
    data: ProjectMemberAdd,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트에 멤버를 추가합니다. 소유자/리더/관리자만 가능합니다."""
    has_permission = await project_service.check_project_permission(current_user, project_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
    try:
        member = await project_service.add_member(project_id, data, db)
        await db.commit()
        return ProjectMemberResponse(**member)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.error(f"프로젝트 멤버 추가 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="멤버 추가에 실패했습니다.")


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    project_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트에서 멤버를 제거합니다. 소유자/리더/관리자만 가능합니다."""
    has_permission = await project_service.check_project_permission(current_user, project_id, db)
    if not has_permission:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="권한이 없습니다.")
    try:
        await project_service.remove_member(project_id, user_id, db)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"프로젝트 멤버 제거 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="멤버 제거에 실패했습니다.")
