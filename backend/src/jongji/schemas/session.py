"""세션 관련 Pydantic 스키마.

활성 세션 조회 응답을 정의합니다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SessionResponse(BaseModel):
    """활성 세션 단건 응답 스키마.

    Attributes:
        id: 세션(RefreshToken) UUID.
        user_agent: 사용자 에이전트 문자열 (device_info 필드 매핑).
        ip_address: 클라이언트 IP 주소.
        created_at: 세션 생성 시각.
        last_used_at: 마지막 사용 시각.
        is_current: 현재 요청에서 사용 중인 세션 여부.
    """

    id: UUID
    user_agent: str | None = None
    ip_address: str | None = None
    created_at: datetime
    last_used_at: datetime | None = None
    is_current: bool = False

    model_config = {"from_attributes": False}


class SessionListResponse(BaseModel):
    """활성 세션 목록 응답 스키마.

    Attributes:
        items: 세션 목록.
    """

    items: list[SessionResponse]
