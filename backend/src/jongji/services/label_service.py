"""라벨 관리 서비스 레이어.

Label CRUD 비즈니스 로직을 처리합니다.
"""

import traceback
import uuid

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.label import Label
from jongji.schemas.project import LabelCreate, LabelUpdate
from jongji.utils.safe_update import safe_update

_UPDATABLE_FIELDS: frozenset[str] = frozenset({"name", "color"})


async def create_label(project_id: uuid.UUID, data: LabelCreate, db: AsyncSession) -> Label:
    """새 라벨을 생성합니다.

    프로젝트 내에서 이름이 유일해야 합니다.

    Args:
        project_id: 소속 프로젝트 UUID.
        data: 라벨 생성 데이터.
        db: 비동기 DB 세션.

    Returns:
        생성된 Label 모델.

    Raises:
        ValueError: 동일 프로젝트 내 이름이 중복되는 경우.
    """
    try:
        existing = await db.execute(
            select(Label).where(
                Label.project_id == project_id,
                Label.name == data.name,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"라벨 이름 '{data.name}'은 이 프로젝트에서 이미 사용 중입니다.")

        label = Label(project_id=project_id, name=data.name, color=data.color)
        db.add(label)
        await db.flush()
        await db.refresh(label)
        return label
    except ValueError:
        raise
    except Exception:
        logger.error(f"라벨 생성 실패: {traceback.format_exc()}")
        raise


async def get_label(label_id: uuid.UUID, db: AsyncSession) -> Label:
    """라벨을 ID로 조회합니다.

    Args:
        label_id: 라벨 UUID.
        db: 비동기 DB 세션.

    Returns:
        Label 모델.

    Raises:
        ValueError: 라벨을 찾을 수 없는 경우.
    """
    result = await db.execute(select(Label).where(Label.id == label_id))
    label = result.scalar_one_or_none()
    if not label:
        raise ValueError("라벨을 찾을 수 없습니다.")
    return label


async def update_label(label_id: uuid.UUID, data: LabelUpdate, db: AsyncSession) -> Label:
    """라벨을 수정합니다.

    Args:
        label_id: 수정할 라벨 UUID.
        data: 수정할 필드 데이터.
        db: 비동기 DB 세션.

    Returns:
        업데이트된 Label 모델.

    Raises:
        ValueError: 라벨을 찾을 수 없는 경우.
    """
    label = await get_label(label_id, db)
    update_data = data.model_dump(exclude_unset=True)
    safe_update(label, update_data, _UPDATABLE_FIELDS)
    await db.flush()
    await db.refresh(label)
    return label


async def delete_label(label_id: uuid.UUID, db: AsyncSession) -> None:
    """라벨을 삭제합니다.

    Args:
        label_id: 삭제할 라벨 UUID.
        db: 비동기 DB 세션.

    Raises:
        ValueError: 라벨을 찾을 수 없는 경우.
    """
    label = await get_label(label_id, db)
    await db.delete(label)
    await db.flush()


async def list_labels(project_id: uuid.UUID, db: AsyncSession) -> list[Label]:
    """프로젝트의 모든 라벨을 반환합니다.

    Args:
        project_id: 프로젝트 UUID.
        db: 비동기 DB 세션.

    Returns:
        Label 목록.
    """
    result = await db.execute(
        select(Label).where(Label.project_id == project_id).order_by(Label.created_at)
    )
    return list(result.scalars().all())
