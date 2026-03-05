"""작업 템플릿 API 엔드포인트.

템플릿 CRUD 및 템플릿으로 작업 생성 엔드포인트를 제공합니다.
"""

import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user, get_db
from jongji.api.tasks import _task_to_response
from jongji.models.user import User
from jongji.schemas.task import TaskResponse
from jongji.schemas.template import TemplateCreate, TemplateResponse, TemplateUpdate
from jongji.services import template_service

router = APIRouter(tags=["templates"])


@router.get("/api/v1/projects/{project_id}/templates", response_model=list[TemplateResponse])
async def list_templates(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트의 작업 템플릿 목록을 반환합니다."""
    return await template_service.list_templates(project_id, db)


@router.post(
    "/api/v1/projects/{project_id}/templates",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    project_id: UUID,
    data: TemplateCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """새 작업 템플릿을 생성합니다."""
    try:
        template = await template_service.create_template(project_id, data, current_user.id, db)
        return template
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"템플릿 생성 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 생성에 실패했습니다.",
        )


@router.put("/api/v1/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """작업 템플릿을 수정합니다."""
    try:
        template = await template_service.update_template(template_id, data, db)
        return template
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"템플릿 수정 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 수정에 실패했습니다.",
        )


@router.delete("/api/v1/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """작업 템플릿을 삭제합니다."""
    try:
        await template_service.delete_template(template_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"템플릿 삭제 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿 삭제에 실패했습니다.",
        )


@router.post(
    "/api/v1/templates/{template_id}/create-task",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_from_template(
    template_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """템플릿을 기반으로 작업을 생성합니다."""
    try:
        task = await template_service.create_task_from_template(template_id, current_user.id, db)
        return _task_to_response(task)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"템플릿으로 작업 생성 실패: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="템플릿으로 작업 생성에 실패했습니다.",
        )
