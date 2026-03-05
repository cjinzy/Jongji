"""Calendar API 엔드포인트 (스텁).

향후 Google Calendar OAuth 연동 시 구현될 엔드포인트를 정의합니다.
현재는 모두 501 Not Implemented를 반환합니다.
"""

import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from loguru import logger

from jongji.api.deps import get_current_user
from jongji.models.user import User

router = APIRouter(tags=["calendar"])


@router.post("/api/v1/projects/{project_id}/calendar/connect")
async def connect_calendar(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Google Calendar를 프로젝트에 연결합니다 (미구현).

    Args:
        project_id: 연결할 프로젝트 UUID.
        user: 인증된 사용자.

    Returns:
        JSONResponse: 501 Not Implemented.
    """
    logger.warning(f"calendar connect called for project {project_id} by user {user.id} — not implemented")
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "Google Calendar 연동은 아직 구현되지 않았습니다."},
    )


@router.delete("/api/v1/projects/{project_id}/calendar/disconnect")
async def disconnect_calendar(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
) -> JSONResponse:
    """Google Calendar 연결을 프로젝트에서 해제합니다 (미구현).

    Args:
        project_id: 연결 해제할 프로젝트 UUID.
        user: 인증된 사용자.

    Returns:
        JSONResponse: 501 Not Implemented.
    """
    logger.warning(f"calendar disconnect called for project {project_id} by user {user.id} — not implemented")
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={"detail": "Google Calendar 연동 해제는 아직 구현되지 않았습니다."},
    )
