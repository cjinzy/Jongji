"""사용자 관리 API 엔드포인트.

프로필 조회/수정, 세션 관리, API Key 관리 등을 제공합니다.
"""

import traceback
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user, get_db
from jongji.models.user import User
from jongji.schemas.user import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    SessionResponse,
    UserResponse,
    UserUpdate,
)
from jongji.services import user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """현재 인증된 사용자의 프로필을 반환합니다."""
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """현재 사용자의 프로필을 수정합니다."""
    try:
        return await user_service.update_user(user, data, db)
    except Exception:
        logger.error(f"프로필 수정 실패: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="프로필 수정에 실패했습니다.")


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """현재 사용자의 계정을 비활성화합니다."""
    try:
        await user_service.deactivate_user(user, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# ── 세션 관리 ──


@router.get("/me/sessions", response_model=list[SessionResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """현재 사용자의 활성 세션 목록을 반환합니다."""
    return await user_service.get_active_sessions(user.id, db)


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """특정 세션을 폐기합니다."""
    try:
        await user_service.revoke_session(user.id, session_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── API Key 관리 ──


@router.get("/me/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """현재 사용자의 API 키 목록을 반환합니다."""
    return await user_service.list_api_keys(user.id, db)


@router.post("/me/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """새 API 키를 생성합니다. raw_key는 이 응답에서만 확인할 수 있습니다."""
    api_key, raw_key = await user_service.create_api_key(user.id, data.name, db)
    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        raw_key=raw_key,
    )


@router.delete("/me/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """API 키를 삭제(비활성화)합니다."""
    try:
        await user_service.delete_api_key(user.id, key_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
