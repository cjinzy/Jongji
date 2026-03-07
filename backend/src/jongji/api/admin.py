"""관리자 전용 API 엔드포인트.

시스템 설정 관리, 사용자 역할 변경, Google OAuth 설정 관리 등을 제공합니다.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_db, require_admin
from jongji.models.user import User
from jongji.schemas.user import (
    GoogleOAuthSettingsResponse,
    GoogleOAuthSettingsUpdate,
    UserResponse,
    UserRoleUpdate,
)
from jongji.services import google_oauth as google_oauth_service
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


@router.get("/oauth/google", response_model=GoogleOAuthSettingsResponse)
async def get_google_oauth_settings(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Google OAuth 설정을 조회합니다 (시크릿 마스킹).

    Args:
        user: 요청한 관리자 사용자.
        db: 비동기 DB 세션.

    Returns:
        GoogleOAuthSettingsResponse: 마스킹된 OAuth 설정 정보.

    Raises:
        HTTPException: 설정이 존재하지 않는 경우 404.
    """
    config = await google_oauth_service.get_oauth_config_masked(db)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google OAuth configuration not found",
        )
    return config


@router.put("/oauth/google", response_model=GoogleOAuthSettingsResponse)
async def update_google_oauth_settings(
    data: GoogleOAuthSettingsUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Google OAuth 설정을 저장합니다.

    Args:
        data: 업데이트할 OAuth 설정 데이터.
        user: 요청한 관리자 사용자.
        db: 비동기 DB 세션.

    Returns:
        GoogleOAuthSettingsResponse: 저장된 OAuth 설정 정보 (마스킹).
    """
    await google_oauth_service.save_oauth_config(
        client_id=data.client_id,
        client_secret=data.client_secret,
        redirect_uri=data.redirect_uri,
        db=db,
    )
    await db.commit()
    config = await google_oauth_service.get_oauth_config_masked(db)
    return config


@router.delete("/oauth/google", status_code=status.HTTP_204_NO_CONTENT)
async def delete_google_oauth_settings(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Google OAuth 설정을 삭제합니다.

    Args:
        user: 요청한 관리자 사용자.
        db: 비동기 DB 세션.

    Raises:
        HTTPException: 설정이 존재하지 않는 경우 404.
    """
    deleted = await google_oauth_service.delete_oauth_config(db)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google OAuth configuration not found",
        )
    await db.commit()
