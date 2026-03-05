"""Task 관련 Pydantic 스키마.

CRUD 요청/응답 직렬화 및 검증을 담당합니다.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from jongji.models.enums import TaskStatus


class TaskCreate(BaseModel):
    """작업 생성 요청 스키마.

    Attributes:
        title: 작업 제목.
        description: 작업 설명 (선택).
        priority: 우선순위 (1-9, 기본 5).
        assignee_id: 담당자 UUID (선택).
        start_date: 시작일 (선택).
        due_date: 종료일 (선택).
    """

    title: str = Field(min_length=1)
    description: str | None = None
    priority: int = Field(default=5, ge=1, le=9)
    assignee_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    """작업 수정 요청 스키마.

    Attributes:
        title: 작업 제목 (선택).
        description: 작업 설명 (선택).
        priority: 우선순위 (선택, 1-9).
        assignee_id: 담당자 UUID (선택).
        start_date: 시작일 (선택).
        due_date: 종료일 (선택).
    """

    title: str | None = None
    description: str | None = None
    priority: int | None = Field(None, ge=1, le=9)
    assignee_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None


class TaskLabelResponse(BaseModel):
    """작업에 연결된 라벨 응답 스키마."""

    label_id: UUID
    name: str | None = None
    color: str | None = None

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    """작업 응답 스키마.

    Attributes:
        id: 작업 UUID.
        project_id: 프로젝트 UUID.
        number: 프로젝트 내 작업 번호.
        title: 작업 제목.
        description: 작업 설명.
        status: 작업 상태.
        priority: 우선순위.
        creator_id: 생성자 UUID.
        assignee_id: 담당자 UUID.
        start_date: 시작일.
        due_date: 종료일.
        is_archived: 보관 여부.
        created_at: 생성 시각.
        updated_at: 수정 시각.
        labels: 연결된 라벨 목록.
        project_key: 프로젝트 키.
    """

    id: UUID
    project_id: UUID
    number: int
    title: str
    description: str | None = None
    status: TaskStatus
    priority: int
    creator_id: UUID
    assignee_id: UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    labels: list[TaskLabelResponse] = []
    project_key: str = ""

    model_config = {"from_attributes": True}


class TaskCloneResponse(TaskResponse):
    """작업 복제 응답 스키마 (TaskResponse 확장)."""

    pass


class TaskStatusUpdate(BaseModel):
    """작업 상태 전환 요청 스키마.

    Attributes:
        status: 변경할 목표 상태.
    """

    status: TaskStatus


class TaskRelationCreate(BaseModel):
    """작업 blocked_by 관계 생성 요청 스키마.

    Attributes:
        blocked_by_task_id: 이 작업을 차단하는 작업의 UUID.
    """

    blocked_by_task_id: UUID


class TaskRelationResponse(BaseModel):
    """작업 관계 응답 스키마.

    Attributes:
        id: 관계 UUID.
        task_id: 대상 작업 UUID.
        blocked_by_task_id: 차단하는 작업 UUID.
    """

    id: UUID
    task_id: UUID
    blocked_by_task_id: UUID

    model_config = {"from_attributes": True}
