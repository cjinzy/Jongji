"""사용자 관리 서비스 레이어.

User CRUD, 세션 관리, API Key 관리 등의 비즈니스 로직을 처리합니다.
"""

import secrets
import traceback
import uuid
from datetime import UTC

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.system import SystemSetting
from jongji.models.user import RefreshToken, User, UserApiKey
from jongji.schemas.user import UserUpdate
from jongji.services.auth_service import hash_password, verify_password  # noqa: F401


async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession) -> User | None:
    """ID로 사용자를 조회합니다.

    Args:
        user_id: 조회할 사용자 UUID.
        db: 비동기 DB 세션.

    Returns:
        User 또는 None.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def update_user(user: User, data: UserUpdate, db: AsyncSession) -> User:
    """사용자 프로필을 업데이트합니다.

    Args:
        user: 수정할 사용자 모델.
        data: 업데이트할 필드 데이터.
        db: 비동기 DB 세션.

    Returns:
        업데이트된 User 모델.
    """
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return user


async def deactivate_user(user: User, db: AsyncSession) -> None:
    """사용자 계정을 비활성화합니다.

    마지막 관리자인 경우 비활성화를 거부합니다.

    Args:
        user: 비활성화할 사용자 모델.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 마지막 관리자인 경우.
    """
    try:
        if user.is_admin:
            admin_count = await db.execute(
                select(func.count()).select_from(User).where(User.is_admin.is_(True), User.is_active.is_(True))
            )
            if admin_count.scalar_one() <= 1:
                raise ValueError("마지막 관리자는 비활성화할 수 없습니다.")

        user.is_active = False
        await db.flush()
    except ValueError:
        raise
    except Exception:
        logger.error(f"사용자 비활성화 실패: {traceback.format_exc()}")
        raise


async def search_users(query: str, db: AsyncSession, limit: int = 20) -> list[User]:
    """사용자를 이름 또는 이메일로 검색합니다.

    Args:
        query: 검색 문자열.
        db: 비동기 DB 세션.
        limit: 최대 결과 수.

    Returns:
        검색 결과 User 목록.
    """
    stmt = (
        select(User)
        .where(User.is_active.is_(True), (User.name.ilike(f"%{query}%")) | (User.email.ilike(f"%{query}%")))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── 세션 관리 ──


async def get_active_sessions(user_id: uuid.UUID, db: AsyncSession) -> list[RefreshToken]:
    """사용자의 활성 세션(리프레시 토큰) 목록을 조회합니다.

    Args:
        user_id: 사용자 UUID.
        db: 비동기 DB 세션.

    Returns:
        활성 RefreshToken 목록.
    """
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    )
    return list(result.scalars().all())


async def revoke_session(user_id: uuid.UUID, session_id: uuid.UUID, db: AsyncSession) -> None:
    """특정 세션을 폐기합니다.

    Args:
        user_id: 사용자 UUID.
        session_id: 폐기할 세션(RefreshToken) UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 해당 세션을 찾을 수 없는 경우.
    """
    from datetime import datetime

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.id == session_id, RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        raise ValueError("세션을 찾을 수 없습니다.")
    token.revoked_at = datetime.now(UTC)
    await db.flush()


# ── API Key 관리 ──


async def create_api_key(user_id: uuid.UUID, name: str, db: AsyncSession) -> tuple[UserApiKey, str]:
    """새 API 키를 생성합니다.

    Args:
        user_id: 사용자 UUID.
        name: API 키 이름.
        db: 비동기 DB 세션.

    Returns:
        (UserApiKey 모델, raw_key) 튜플. raw_key는 최초 1회만 노출됩니다.
    """
    raw_key = f"jk_{secrets.token_urlsafe(32)}"
    key_hash = await hash_password(raw_key)

    api_key = UserApiKey(
        user_id=user_id,
        name=name,
        key_hash=key_hash,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)
    return api_key, raw_key


async def list_api_keys(user_id: uuid.UUID, db: AsyncSession) -> list[UserApiKey]:
    """사용자의 API 키 목록을 조회합니다.

    Args:
        user_id: 사용자 UUID.
        db: 비동기 DB 세션.

    Returns:
        UserApiKey 목록.
    """
    result = await db.execute(select(UserApiKey).where(UserApiKey.user_id == user_id, UserApiKey.is_active.is_(True)))
    return list(result.scalars().all())


async def delete_api_key(user_id: uuid.UUID, key_id: uuid.UUID, db: AsyncSession) -> None:
    """API 키를 비활성화합니다.

    Args:
        user_id: 사용자 UUID.
        key_id: 삭제할 API 키 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 해당 API 키를 찾을 수 없는 경우.
    """
    result = await db.execute(
        select(UserApiKey).where(UserApiKey.id == key_id, UserApiKey.user_id == user_id, UserApiKey.is_active.is_(True))
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise ValueError("API 키를 찾을 수 없습니다.")
    api_key.is_active = False
    await db.flush()


# ── 관리자 설정 ──


async def get_system_settings(db: AsyncSession) -> dict[str, str]:
    """모든 시스템 설정을 딕셔너리로 반환합니다.

    Args:
        db: 비동기 DB 세션.

    Returns:
        {key: value} 형태의 시스템 설정 딕셔너리.
    """
    result = await db.execute(select(SystemSetting))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}


async def update_system_settings(data: dict[str, str], db: AsyncSession) -> dict[str, str]:
    """시스템 설정을 업데이트합니다.

    Args:
        data: {key: value} 형태의 업데이트할 설정.
        db: 비동기 DB 세션.

    Returns:
        업데이트된 전체 시스템 설정.
    """
    for key, value in data.items():
        existing = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
        setting = existing.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            db.add(SystemSetting(key=key, value=value))
    await db.flush()
    return await get_system_settings(db)


async def update_user_role(
    target_user_id: uuid.UUID, is_admin: bool, db: AsyncSession
) -> User:
    """사용자의 관리자 역할을 변경합니다.

    Args:
        target_user_id: 대상 사용자 UUID.
        is_admin: 관리자 여부.
        db: 비동기 DB 세션.

    Returns:
        업데이트된 User 모델.

    Raises:
        ValueError: 사용자를 찾을 수 없거나, 마지막 관리자의 권한을 해제하려는 경우.
    """
    result = await db.execute(select(User).where(User.id == target_user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise ValueError("사용자를 찾을 수 없습니다.")

    if not is_admin and target.is_admin:
        admin_count = await db.execute(
            select(func.count()).select_from(User).where(User.is_admin.is_(True), User.is_active.is_(True))
        )
        if admin_count.scalar_one() <= 1:
            raise ValueError("마지막 관리자의 권한을 해제할 수 없습니다.")

    target.is_admin = is_admin
    await db.flush()
    await db.refresh(target)
    return target
