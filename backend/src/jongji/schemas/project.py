"""Project/Label 관련 Pydantic 스키마.

프로젝트 CRUD, 멤버 관리, 라벨 CRUD의 요청/응답 직렬화와 검증을 담당합니다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """프로젝트 생성 요청 스키마.

    Attributes:
        name: 프로젝트 이름.
        key: 대문자로 시작하는 2~10자 영숫자 식별 키 (예: MYPROJ).
        team_id: 소속 팀 UUID.
        description: 선택적 설명.
        is_private: 비공개 여부 (기본값 False).
    """

    name: str = Field(min_length=1, max_length=100)
    key: str = Field(pattern="^[A-Z][A-Z0-9]{1,9}$")
    team_id: UUID
    description: str | None = None
    is_private: bool = False


class ProjectUpdate(BaseModel):
    """프로젝트 수정 요청 스키마.

    Attributes:
        name: 변경할 프로젝트 이름.
        description: 변경할 설명.
        is_private: 변경할 비공개 여부.
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    is_private: bool | None = None


class ProjectResponse(BaseModel):
    """프로젝트 응답 스키마.

    Attributes:
        id: 프로젝트 UUID.
        team_id: 소속 팀 UUID.
        name: 프로젝트 이름.
        key: 식별 키.
        description: 설명.
        is_private: 비공개 여부.
        is_archived: 아카이브 여부.
        owner_id: 소유자 UUID.
        task_counter: 작업 카운터.
        created_at: 생성 시각.
    """

    id: UUID
    team_id: UUID
    name: str
    key: str
    description: str | None = None
    is_private: bool
    is_archived: bool
    owner_id: UUID
    task_counter: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectMemberAdd(BaseModel):
    """프로젝트 멤버 추가 요청 스키마.

    Attributes:
        user_id: 추가할 사용자 UUID.
        role: 프로젝트 내 역할 (기본값 member).
    """

    user_id: UUID
    role: str = "member"


class ProjectMemberResponse(BaseModel):
    """프로젝트 멤버 응답 스키마.

    Attributes:
        id: 멤버 레코드 UUID.
        user_id: 사용자 UUID.
        user_name: 사용자 이름.
        user_email: 사용자 이메일.
        role: 프로젝트 내 역할.
        min_alert_priority: 최소 알림 우선순위.
        created_at: 추가 시각.
    """

    id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    role: str
    min_alert_priority: int
    created_at: datetime

    model_config = {"from_attributes": True}


class LabelCreate(BaseModel):
    """라벨 생성 요청 스키마.

    Attributes:
        name: 라벨 이름 (프로젝트 내 유일).
        color: #RRGGBB 형식의 색상 코드.
    """

    name: str = Field(min_length=1, max_length=50)
    color: str = Field(pattern="^#[0-9A-Fa-f]{6}$")


class LabelUpdate(BaseModel):
    """라벨 수정 요청 스키마.

    Attributes:
        name: 변경할 라벨 이름.
        color: 변경할 색상 코드.
    """

    name: str | None = Field(None, min_length=1, max_length=50)
    color: str | None = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class LabelResponse(BaseModel):
    """라벨 응답 스키마.

    Attributes:
        id: 라벨 UUID.
        name: 라벨 이름.
        color: 색상 코드.
        project_id: 소속 프로젝트 UUID.
        created_at: 생성 시각.
    """

    id: UUID
    name: str
    color: str
    project_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
