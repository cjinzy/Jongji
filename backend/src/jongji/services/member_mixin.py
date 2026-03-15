"""멤버 관리 공용 헬퍼.

ProjectMember / TeamMember 공통 패턴(중복 체크·조회·삭제·사용자 조회·dict 변환)을
재사용 가능한 private 헬퍼로 제공합니다.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from jongji.models.user import User


async def fetch_user_or_raise(user_id: uuid.UUID, db: AsyncSession) -> User:
    """사용자를 조회하고 없으면 ValueError를 발생시킵니다.

    Args:
        user_id: 사용자 UUID.
        db: 비동기 DB 세션.

    Returns:
        조회된 User 모델.

    Raises:
        ValueError: 사용자를 찾을 수 없는 경우.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("사용자를 찾을 수 없습니다.")
    return user


async def fetch_member_or_none[M: DeclarativeBase](
    model: type[M],
    filter_clause: Any,
    db: AsyncSession,
) -> M | None:
    """조건에 맞는 멤버 레코드 하나를 조회합니다.

    Args:
        model: 멤버 ORM 모델 클래스 (ProjectMember, TeamMember 등).
        filter_clause: SQLAlchemy 필터 표현식.
        db: 비동기 DB 세션.

    Returns:
        멤버 레코드 또는 None.
    """
    result = await db.execute(select(model).where(filter_clause))
    return result.scalar_one_or_none()


async def assert_not_duplicate[M: DeclarativeBase](
    model: type[M],
    filter_clause: Any,
    error_message: str,
    db: AsyncSession,
) -> None:
    """멤버 중복 여부를 검사하고 이미 존재하면 ValueError를 발생시킵니다.

    Args:
        model: 멤버 ORM 모델 클래스.
        filter_clause: SQLAlchemy 필터 표현식.
        error_message: 중복 시 ValueError 메시지.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 이미 해당 멤버가 존재하는 경우.
    """
    existing = await fetch_member_or_none(model, filter_clause, db)
    if existing is not None:
        raise ValueError(error_message)


async def delete_member_or_raise[M: DeclarativeBase](
    model: type[M],
    filter_clause: Any,
    error_message: str,
    db: AsyncSession,
) -> None:
    """멤버 레코드를 조회 후 삭제합니다. 없으면 ValueError를 발생시킵니다.

    Args:
        model: 멤버 ORM 모델 클래스.
        filter_clause: SQLAlchemy 필터 표현식.
        error_message: 레코드가 없을 때 ValueError 메시지.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 멤버 레코드를 찾을 수 없는 경우.
    """
    member = await fetch_member_or_none(model, filter_clause, db)
    if not member:
        raise ValueError(error_message)
    await db.delete(member)
    await db.flush()


def build_member_dict(pm: Any, user: User) -> dict:
    """멤버 레코드와 사용자 정보를 API 응답용 딕셔너리로 변환합니다.

    ``min_alert_priority`` 속성이 없는 모델(예: TeamMember)은 None으로 처리합니다.

    Args:
        pm: 멤버 ORM 레코드 (ProjectMember, TeamMember 등).
        user: 연결된 User 모델.

    Returns:
        API 응답용 멤버 정보 딕셔너리.
    """
    return {
        "id": pm.id,
        "user_id": pm.user_id,
        "user_name": user.name,
        "user_email": user.email,
        "role": pm.role,
        "min_alert_priority": getattr(pm, "min_alert_priority", None),
        "created_at": pm.created_at,
    }
