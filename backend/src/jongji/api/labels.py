"""라벨 관리 API 엔드포인트.

프로젝트별 라벨 CRUD를 제공합니다.
- 프로젝트 스코프: GET/POST /api/v1/projects/{project_id}/labels
- 라벨 스코프: PUT/DELETE /api/v1/labels/{label_id}
"""

import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_db, require_label_access, require_project_access
from jongji.models.user import User
from jongji.schemas.project import LabelCreate, LabelResponse, LabelUpdate
from jongji.services import label_service

router = APIRouter(tags=["labels"])


@router.get("/api/v1/projects/{project_id}/labels", response_model=list[LabelResponse])
async def list_labels(
    project_id: UUID,
    current_user: User = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트의 모든 라벨을 반환합니다."""
    labels = await label_service.list_labels(project_id, db)
    return [LabelResponse.model_validate(lb) for lb in labels]


@router.post("/api/v1/projects/{project_id}/labels", response_model=LabelResponse, status_code=status.HTTP_201_CREATED)
async def create_label(
    project_id: UUID,
    data: LabelCreate,
    current_user: User = Depends(require_project_access),
    db: AsyncSession = Depends(get_db),
):
    """프로젝트에 새 라벨을 생성합니다."""
    try:
        label = await label_service.create_label(project_id, data, db)
        await db.commit()
        return LabelResponse.model_validate(label)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        logger.error(f"라벨 생성 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="라벨 생성에 실패했습니다.")


@router.put("/api/v1/labels/{label_id}", response_model=LabelResponse)
async def update_label(
    label_id: UUID,
    data: LabelUpdate,
    current_user: User = Depends(require_label_access),
    db: AsyncSession = Depends(get_db),
):
    """라벨을 수정합니다."""
    try:
        label = await label_service.update_label(label_id, data, db)
        await db.commit()
        return LabelResponse.model_validate(label)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"라벨 수정 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="라벨 수정에 실패했습니다.")


@router.delete("/api/v1/labels/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_label(
    label_id: UUID,
    current_user: User = Depends(require_label_access),
    db: AsyncSession = Depends(get_db),
):
    """라벨을 삭제합니다."""
    try:
        await label_service.delete_label(label_id, db)
        await db.commit()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        logger.error(f"라벨 삭제 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="라벨 삭제에 실패했습니다.")
