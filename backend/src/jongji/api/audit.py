"""감사 로그 API 엔드포인트.

팀 리더 이상의 권한이 있는 사용자가 감사 로그를 조회하는 엔드포인트를 제공합니다.
"""

import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user, get_db
from jongji.models.team import TeamMember
from jongji.models.user import User
from jongji.schemas.audit import AuditLogListResponse, AuditLogResponse
from jongji.services import audit_service

router = APIRouter(prefix="/api/v1/audit-logs", tags=["audit"])


async def _require_team_leader(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """팀 리더 또는 관리자 권한을 검증합니다.

    Args:
        current_user: 현재 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        검증된 User 모델.

    Raises:
        HTTPException: 권한이 없는 경우 403.
    """
    if current_user.is_admin:
        return current_user

    result = await db.execute(
        select(TeamMember).where(
            TeamMember.user_id == current_user.id,
            TeamMember.role == "leader",
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="팀 리더 이상의 권한이 필요합니다.",
        )
    return current_user


@router.get("", response_model=AuditLogListResponse)
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    _current_user: User = Depends(_require_team_leader),
    db: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    """감사 로그 목록을 조회합니다.

    팀 리더 또는 관리자만 접근할 수 있습니다.

    Args:
        limit: 페이지 크기 (1~200, 기본 50).
        offset: 오프셋 (기본 0).
        action: 액션 필터.
        resource_type: 리소스 유형 필터.
        user_id: 사용자 UUID 필터.
        _current_user: 권한 검증된 현재 사용자 (unused, 권한 체크용).
        db: 비동기 DB 세션.

    Returns:
        AuditLogListResponse: 로그 목록과 페이지네이션 정보.
    """
    try:
        logs, total = await audit_service.list_audit_logs(
            db,
            limit=limit,
            offset=offset,
            action=action,
            resource_type=resource_type,
            user_id=user_id,
        )
        return AuditLogListResponse(
            items=[AuditLogResponse.model_validate(log) for log in logs],
            total=total,
            limit=limit,
            offset=offset,
        )
    except HTTPException:
        raise
    except Exception:
        logger.error(f"감사 로그 조회 API 오류:\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 오류가 발생했습니다.")
