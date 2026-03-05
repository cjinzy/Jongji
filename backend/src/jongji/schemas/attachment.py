"""첨부파일 관련 Pydantic 스키마.

첨부파일 응답 직렬화를 담당합니다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    """첨부파일 응답 스키마.

    Attributes:
        id: 첨부파일 UUID.
        task_id: 연결된 작업 UUID (임시 파일이면 None).
        comment_id: 연결된 댓글 UUID.
        filename: 원본 파일명.
        content_type: MIME 타입.
        size_bytes: 파일 크기 (바이트).
        is_temp: 임시 파일 여부.
        created_at: 생성 시각.
    """

    id: UUID
    task_id: UUID | None
    comment_id: UUID | None
    filename: str
    content_type: str
    size_bytes: int
    is_temp: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AttachmentListResponse(BaseModel):
    """첨부파일 목록 응답 스키마.

    Attributes:
        items: 첨부파일 목록.
    """

    items: list[AttachmentResponse]
