"""댓글 관련 Pydantic 스키마.

댓글 CRUD 요청/응답 직렬화 및 검증을 담당합니다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    """댓글 생성 요청 스키마.

    Attributes:
        content: 댓글 내용 (Markdown, @mention 지원).
    """

    content: str = Field(min_length=1)


class CommentUpdate(BaseModel):
    """댓글 수정 요청 스키마.

    Attributes:
        content: 수정할 댓글 내용 (Markdown, @mention 지원).
    """

    content: str = Field(min_length=1)


class CommentResponse(BaseModel):
    """댓글 응답 스키마.

    Attributes:
        id: 댓글 UUID.
        task_id: 작업 UUID.
        user_id: 작성자 UUID.
        content: 댓글 내용.
        created_at: 생성 시각.
        updated_at: 수정 시각.
    """

    id: UUID
    task_id: UUID
    user_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
