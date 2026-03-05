"""세션 관리 API 엔드포인트.

현재 사용자의 활성 세션 목록 조회 및 특정 세션 로그아웃 기능을 제공합니다.
"""

import traceback
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user, get_db
from jongji.models.user import RefreshToken, User
from jongji.schemas.session import SessionListResponse, SessionResponse

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
) -> SessionListResponse:
    """현재 사용자의 활성 세션 목록을 반환합니다.

    만료되지 않고 revoke되지 않은 refresh_token을 세션으로 간주합니다.

    Args:
        current_user: 현재 인증된 사용자.
        db: 비동기 DB 세션.
        refresh_token: 현재 요청의 refresh_token 쿠키 (is_current 판별용).

    Returns:
        SessionListResponse: 활성 세션 목록.
    """
    try:
        now = datetime.now(UTC)
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        tokens = list(result.scalars().all())

        items = []
        for token in tokens:
            items.append(
                SessionResponse(
                    id=token.id,
                    user_agent=token.device_info,
                    ip_address=None,
                    created_at=token.created_at,
                    last_used_at=None,
                    is_current=False,
                )
            )

        return SessionListResponse(items=items)
    except Exception:
        logger.error(f"세션 목록 조회 오류:\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 오류가 발생했습니다.")


@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """특정 세션을 로그아웃(revoke)합니다.

    자신의 세션만 로그아웃할 수 있습니다.

    Args:
        session_id: revoke할 세션(RefreshToken) UUID.
        current_user: 현재 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        dict: 처리 결과 메시지.

    Raises:
        HTTPException: 세션이 없거나 권한이 없으면 404.
    """
    try:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.id == session_id,
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        token = result.scalar_one_or_none()
        if not token:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다.")

        token.revoked_at = datetime.now(UTC)
        await db.flush()
        await db.commit()
        logger.info(f"세션 revoke: session_id={session_id}, user_id={current_user.id}")
        return {"detail": "세션이 로그아웃되었습니다."}
    except HTTPException:
        raise
    except Exception:
        logger.error(f"세션 revoke 오류:\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="서버 오류가 발생했습니다.")
