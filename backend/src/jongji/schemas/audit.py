"""감사 로그 관련 Pydantic 스키마.

감사 로그 조회 응답 및 필터 파라미터를 정의합니다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """감사 로그 단건 응답 스키마.

    Attributes:
        id: 로그 UUID.
        user_id: 행위자 사용자 UUID (익명이면 None).
        action: 수행된 액션 문자열.
        resource_type: 리소스 유형.
        resource_id: 대상 리소스 UUID (없을 수 있음).
        details: 추가 상세 정보 (JSON).
        source: 요청 출처 ("api" | "mcp").
        ip_address: 클라이언트 IP 주소.
        created_at: 기록 시각.
    """

    id: UUID
    user_id: UUID | None = None
    action: str
    resource_type: str
    resource_id: UUID | None = None
    details: dict | None = None
    source: str
    ip_address: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    """감사 로그 목록 응답 스키마.

    Attributes:
        items: 로그 목록.
        total: 전체 로그 수.
        limit: 페이지 크기.
        offset: 오프셋.
    """

    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int
