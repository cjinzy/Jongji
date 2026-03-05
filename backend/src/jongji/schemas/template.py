"""Task Template 관련 Pydantic 스키마.

템플릿 CRUD 요청/응답 직렬화 및 검증을 담당합니다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    """템플릿 생성 요청 스키마.

    Attributes:
        name: 템플릿 이름.
        title_template: 작업 제목 템플릿 문자열.
        description: 작업 설명 (선택).
        priority: 우선순위 (1-9, 기본 5).
        tags: 태그 목록 (선택).
    """

    name: str = Field(min_length=1)
    title_template: str = Field(min_length=1)
    description: str | None = None
    priority: int = Field(default=5, ge=1, le=9)
    tags: list[str] | None = None


class TemplateUpdate(BaseModel):
    """템플릿 수정 요청 스키마.

    모든 필드는 선택적입니다.

    Attributes:
        name: 템플릿 이름 (선택).
        title_template: 작업 제목 템플릿 문자열 (선택).
        description: 작업 설명 (선택).
        priority: 우선순위 (선택, 1-9).
        tags: 태그 목록 (선택).
    """

    name: str | None = None
    title_template: str | None = None
    description: str | None = None
    priority: int | None = Field(None, ge=1, le=9)
    tags: list[str] | None = None


class TemplateResponse(BaseModel):
    """템플릿 응답 스키마.

    Attributes:
        id: 템플릿 UUID.
        project_id: 프로젝트 UUID.
        name: 템플릿 이름.
        title_template: 작업 제목 템플릿.
        description: 작업 설명.
        priority: 우선순위.
        tags: 태그 목록.
        created_by: 생성자 UUID.
        created_at: 생성 시각.
        updated_at: 수정 시각.
    """

    id: UUID
    project_id: UUID
    name: str
    title_template: str
    description: str | None = None
    priority: int
    tags: list[str] | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
