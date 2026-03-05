"""전문 검색 관련 Pydantic 스키마."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from jongji.models.enums import TaskStatus


class SearchQuery(BaseModel):
    """검색 요청 파라미터 스키마."""

    query: str = Field(..., min_length=1, description="검색어")
    project_id: uuid.UUID | None = Field(None, description="프로젝트 필터 UUID")
    tag: str | None = Field(None, description="태그 필터")
    status: TaskStatus | None = Field(None, description="상태 필터")
    assignee_id: uuid.UUID | None = Field(None, description="담당자 필터 UUID")
    priority: int | None = Field(None, ge=1, le=9, description="우선순위 필터 (1-9)")
    limit: int = Field(20, ge=1, le=100, description="결과 수 제한")
    offset: int = Field(0, ge=0, description="오프셋")


class SearchResultItem(BaseModel):
    """개별 검색 결과 항목 스키마."""

    type: Literal["task", "comment"] = Field(..., description="결과 유형")
    task_id: uuid.UUID = Field(..., description="작업 UUID")
    task_number: int = Field(..., description="프로젝트 내 작업 번호")
    task_title: str = Field(..., description="작업 제목")
    project_key: str = Field(..., description="프로젝트 키 (예: PROJ)")
    highlight: str = Field(..., description="매칭된 텍스트 하이라이트")
    score: float = Field(..., description="관련성 점수")


class SearchResponse(BaseModel):
    """검색 응답 스키마."""

    items: list[SearchResultItem] = Field(default_factory=list, description="검색 결과 목록")
    total: int = Field(..., description="총 결과 수")
    query: str = Field(..., description="원본 검색어")
