"""Team 관련 Pydantic 스키마.

팀 CRUD 요청/응답, 멤버 관리, 초대 링크 등의 직렬화/검증을 담당합니다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    """팀 생성 요청 스키마.

    Attributes:
        name: 팀 이름.
        description: 팀 설명 (선택).
    """

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class TeamUpdate(BaseModel):
    """팀 수정 요청 스키마.

    Attributes:
        name: 팀 이름 (선택).
        description: 팀 설명 (선택).
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class TeamResponse(BaseModel):
    """팀 응답 스키마.

    Attributes:
        id: 팀 UUID.
        name: 팀 이름.
        description: 팀 설명.
        is_archived: 아카이브 여부.
        created_by: 생성자 UUID.
        member_count: 멤버 수.
        created_at: 생성 시각.
    """

    id: UUID
    name: str
    slug: str
    description: str | None
    is_archived: bool
    created_by: UUID
    member_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberAdd(BaseModel):
    """팀 멤버 추가 요청 스키마.

    Attributes:
        user_id: 추가할 사용자 UUID.
        role: 역할 (leader 또는 member).
    """

    user_id: UUID
    role: str = Field(default="member", pattern=r"^(leader|member)$")


class TeamMemberResponse(BaseModel):
    """팀 멤버 응답 스키마.

    Attributes:
        id: TeamMember UUID.
        user_id: 사용자 UUID.
        user_name: 사용자 이름.
        user_email: 사용자 이메일.
        role: 역할.
        created_at: 멤버십 생성 시각.
    """

    id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamInviteCreate(BaseModel):
    """팀 초대 링크 생성 요청 스키마.

    Attributes:
        expires_in_days: 초대 링크 유효 기간(일), 기본값 7일.
        max_uses: 최대 사용 횟수 (None이면 무제한).
    """

    expires_in_days: int = Field(default=7, ge=1, le=365)
    max_uses: int | None = Field(default=None, ge=1)


class TeamInviteResponse(BaseModel):
    """팀 초대 링크 응답 스키마.

    Attributes:
        id: TeamInvite UUID.
        team_id: 팀 UUID.
        token: 초대 토큰.
        expires_at: 만료 시각.
        max_uses: 최대 사용 횟수.
        use_count: 현재 사용 횟수.
        is_active: 활성 여부.
        created_at: 생성 시각.
    """

    id: UUID
    team_id: UUID
    token: str
    expires_at: datetime
    max_uses: int | None
    use_count: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
