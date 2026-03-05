"""태그 관련 Pydantic 스키마.

태그 목록 및 태그별 작업 조회 응답 직렬화를 담당합니다.
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel

from jongji.models.enums import TaskStatus


class TagResponse(BaseModel):
    """태그 응답 스키마.

    Attributes:
        tag: 태그 이름.
        count: 프로젝트 내 사용 횟수.
    """

    tag: str
    count: int


class TagTaskItem(BaseModel):
    """태그별 작업 목록에서 사용하는 작업 항목 스키마.

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

    model_config = {"from_attributes": True}


class TagTasksResponse(BaseModel):
    """태그별 작업 목록 응답 스키마.

    Attributes:
        tag: 조회한 태그 이름.
        tasks: 해당 태그가 붙은 작업 목록.
    """

    tag: str
    tasks: list[TagTaskItem]
