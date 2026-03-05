"""Calendar 서비스 스텁.

향후 Google Calendar OAuth 연동 시 구현될 함수들을 정의합니다.
"""

import uuid

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession


async def connect_google_calendar(
    project_id: uuid.UUID,
    auth_code: str,
    db: AsyncSession,
) -> None:
    """Google Calendar를 프로젝트에 연결합니다 (미구현).

    Args:
        project_id: 연결할 프로젝트 UUID.
        auth_code: Google OAuth 인증 코드.
        db: 비동기 DB 세션.

    Raises:
        NotImplementedError: 항상 발생 — 향후 구현 예정.
    """
    logger.warning(f"connect_google_calendar called for project {project_id} — not implemented")
    raise NotImplementedError("Google Calendar 연동은 아직 구현되지 않았습니다.")


async def disconnect_google_calendar(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """Google Calendar 연결을 프로젝트에서 해제합니다 (미구현).

    Args:
        project_id: 연결 해제할 프로젝트 UUID.
        db: 비동기 DB 세션.

    Raises:
        NotImplementedError: 항상 발생 — 향후 구현 예정.
    """
    logger.warning(f"disconnect_google_calendar called for project {project_id} — not implemented")
    raise NotImplementedError("Google Calendar 연동 해제는 아직 구현되지 않았습니다.")
