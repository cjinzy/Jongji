"""관리자 전용 API 엔드포인트.

시스템 설정 관리, 사용자 역할 변경 등을 제공합니다.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_db, require_admin
from jongji.models.user import User
from jongji.schemas.user import UserResponse, UserRoleUpdate
from jongji.services import user_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/settings")
async def get_settings(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """모든 시스템 설정을 반환합니다."""
    return await user_service.get_system_settings(db)


@router.put("/settings")
async def update_settings(
    data: dict[str, str],
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """시스템 설정을 업데이트합니다."""
    result = await user_service.update_system_settings(data, db)
    await db.commit()
    return result


@router.put("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    data: UserRoleUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """사용자의 관리자 역할을 변경합니다."""
    try:
        updated = await user_service.update_user_role(user_id, data.is_admin, db)
        await db.commit()
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
