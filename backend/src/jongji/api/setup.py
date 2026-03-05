"""Setup Wizard API 라우터.

초기 설정 마법사의 상태 확인, 관리자 생성, 시스템 설정, 완료 처리를 제공합니다.
"""

import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.config import settings
from jongji.database import get_db
from jongji.models.system import SystemSetting
from jongji.models.user import User
from jongji.schemas.user import (
    SetupAdminCreate,
    SetupStatusResponse,
    SystemSettingsUpdate,
    UserResponse,
)
from jongji.services.auth_service import (
    check_setup_completed,
    get_user_count,
    hash_password,
)

router = APIRouter(prefix="/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusResponse)
async def setup_status(db: AsyncSession = Depends(get_db)):
    """초기 설정 상태를 확인합니다.

    Args:
        db: 비동기 DB 세션.

    Returns:
        SetupStatusResponse: 설정 완료 여부와 OAuth 사용 가능 여부.
    """
    completed = await check_setup_completed(db)
    oauth_available = bool(settings.GOOGLE_CLIENT_ID)
    return SetupStatusResponse(
        setup_completed=completed,
        oauth_available=oauth_available,
    )


@router.post("/admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_setup_admin(
    data: SetupAdminCreate,
    db: AsyncSession = Depends(get_db),
):
    """초기 관리자 계정을 생성합니다.

    Race condition 방지를 위해 트랜잭션 내에서 사용자 수를 확인합니다.

    Args:
        data: 관리자 생성 요청 데이터.
        db: 비동기 DB 세션.

    Returns:
        UserResponse: 생성된 관리자 정보.
    """
    # Advisory lock으로 동시 요청 방지 (TOCTOU 레이스 컨디션 방어)
    await db.execute(text("SELECT pg_advisory_xact_lock(42)"))

    completed = await check_setup_completed(db)
    if completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed",
        )

    user_count = await get_user_count(db)
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin user already exists",
        )

    try:
        admin = User(
            email=data.email,
            name=data.name,
            password_hash=await hash_password(data.password),
            is_admin=True,
        )
        db.add(admin)
        await db.flush()
    except Exception:
        logger.error(f"Failed to create admin: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    await db.commit()
    return UserResponse.model_validate(admin)


@router.post("/settings")
async def save_setup_settings(
    data: SystemSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """시스템 설정을 저장합니다.

    setup_completed=true인 경우 변경을 거부합니다.

    Args:
        data: 설정 업데이트 요청 데이터.
        db: 비동기 DB 세션.

    Returns:
        dict: 저장 성공 메시지.
    """
    completed = await check_setup_completed(db)
    if completed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup already completed. Use admin settings instead.",
        )

    settings_map = {
        "app_name": data.app_name,
        "timezone": data.timezone,
        "default_locale": data.default_locale,
    }

    for key, value in settings_map.items():
        if value is not None:
            await _upsert_setting(db, key, value)

    await db.commit()
    return {"detail": "Settings saved"}


@router.post("/complete")
async def complete_setup(db: AsyncSession = Depends(get_db)):
    """초기 설정을 완료합니다.

    관리자가 존재해야 하며, 이미 완료된 경우 409를 반환합니다.

    Args:
        db: 비동기 DB 세션.

    Returns:
        dict: 완료 성공 메시지.
    """
    # Advisory lock으로 동시 요청 방지
    await db.execute(text("SELECT pg_advisory_xact_lock(42)"))

    completed = await check_setup_completed(db)
    if completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup already completed",
        )

    user_count = await get_user_count(db)
    if user_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin user must be created first",
        )

    await _upsert_setting(db, "setup_completed", "true")
    await db.commit()
    return {"detail": "Setup completed"}


async def _upsert_setting(db: AsyncSession, key: str, value: str) -> None:
    """시스템 설정을 upsert합니다.

    Args:
        db: 비동기 DB 세션.
        key: 설정 키.
        value: 설정 값.
    """
    from sqlalchemy import select

    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
    await db.flush()
