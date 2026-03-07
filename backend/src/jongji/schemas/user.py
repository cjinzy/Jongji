"""User 관련 Pydantic 스키마.

CRUD 요청/응답, 세션, API Key 등의 직렬화/검증을 담당합니다.
"""

import re
from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """회원가입 요청 스키마.

    Attributes:
        email: 이메일 주소.
        password: 비밀번호 (최소 8자, 대문자/숫자 포함).
        name: 사용자 이름.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """비밀번호 복잡성 검증: 대문자 + 숫자 포함."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("비밀번호에 대문자가 최소 1자 포함되어야 합니다.")
        if not re.search(r"[0-9]", v):
            raise ValueError("비밀번호에 숫자가 최소 1자 포함되어야 합니다.")
        return v


class UserLogin(BaseModel):
    """로그인 요청 스키마.

    Attributes:
        email: 이메일 주소.
        password: 비밀번호.
    """

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """토큰 응답 스키마.

    Attributes:
        access_token: JWT 액세스 토큰.
        token_type: 토큰 타입.
    """

    access_token: str
    token_type: str = "bearer"


class SetupStatusResponse(BaseModel):
    """Setup Wizard 상태 응답 스키마.

    Attributes:
        setup_completed: 초기 설정 완료 여부.
        oauth_available: Google OAuth 사용 가능 여부.
    """

    setup_completed: bool
    oauth_available: bool


class SetupAdminCreate(BaseModel):
    """Setup 관리자 생성 요청 스키마.

    Attributes:
        email: 관리자 이메일.
        password: 관리자 비밀번호 (최소 8자, 대문자/숫자 포함).
        name: 관리자 이름.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """비밀번호 복잡성 검증: 대문자 + 숫자 포함."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("비밀번호에 대문자가 최소 1자 포함되어야 합니다.")
        if not re.search(r"[0-9]", v):
            raise ValueError("비밀번호에 숫자가 최소 1자 포함되어야 합니다.")
        return v


class SetupInitRequest(BaseModel):
    """초기 설정 원스텝 완료 요청 스키마 (프론트엔드 SetupPage용).

    Attributes:
        admin_name: 관리자 이름.
        admin_email: 관리자 이메일.
        admin_password: 관리자 비밀번호 (최소 8자, 대문자/숫자 포함).
        app_name: 애플리케이션 이름 (기본값: Jongji).
    """

    admin_name: str = Field(min_length=1)
    admin_email: EmailStr
    admin_password: str = Field(min_length=8, max_length=128)
    app_name: str | None = "Jongji"

    @field_validator("admin_password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """비밀번호 복잡성 검증: 대문자 + 숫자 포함."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("비밀번호에 대문자가 최소 1자 포함되어야 합니다.")
        if not re.search(r"[0-9]", v):
            raise ValueError("비밀번호에 숫자가 최소 1자 포함되어야 합니다.")
        return v


class SystemSettingsUpdate(BaseModel):
    """시스템 설정 업데이트 요청 스키마.

    Attributes:
        app_name: 애플리케이션 이름.
        timezone: 기본 시간대.
        default_locale: 기본 언어.
    """

    app_name: str | None = None
    timezone: str | None = None
    default_locale: str | None = None


class UserUpdate(BaseModel):
    """사용자 프로필 수정 스키마."""

    name: str | None = None
    locale: str | None = Field(None, pattern=r"^(ko|en)$")
    timezone: str | None = None
    daily_summary_time: time | None = None
    dnd_start: time | None = None
    dnd_end: time | None = None
    avatar_url: str | None = None


class UserResponse(BaseModel):
    """사용자 전체 응답 스키마."""

    id: UUID
    email: str
    name: str
    avatar_url: str | None = None
    is_admin: bool
    is_active: bool
    locale: str
    timezone: str | None = None
    onboarding_completed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    """활성 세션 정보 응답 스키마."""

    id: UUID
    device_info: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    """API 키 생성 요청 스키마."""

    name: str = Field(min_length=1, max_length=100)


class ApiKeyResponse(BaseModel):
    """API 키 정보 응답 스키마 (실제 키 미포함)."""

    id: UUID
    name: str
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    """API 키 생성 직후 응답 스키마 (raw key 포함, 최초 1회만 노출)."""

    raw_key: str


class UserRoleUpdate(BaseModel):
    """관리자 역할 변경 요청 스키마."""

    is_admin: bool
