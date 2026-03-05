"""사용자 관련 모델 (users, refresh_tokens, user_api_keys)."""

import uuid
from datetime import UTC, datetime, time

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jongji.database import Base


class User(Base):
    """사용자 계정 정보를 저장하는 모델.

    이메일/비밀번호 또는 Google OAuth를 통한 인증을 지원하며,
    TOTP, Passkey 등 다중 인증 수단과 DND 설정을 포함합니다.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    google_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    locale: Mapped[str] = mapped_column(String, default="ko")
    timezone: Mapped[str | None] = mapped_column(String, nullable=True)
    daily_summary_time: Mapped[time] = mapped_column(Time, default=time(0, 0))
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    dnd_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    dnd_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    passkey_credential: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    totp_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    login_fail_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["UserApiKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    """리프레시 토큰 저장 모델.

    사용자 인증 세션을 유지하기 위한 JWT 리프레시 토큰의 해시와
    만료 시간, 디바이스 정보 등을 저장합니다.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("idx_refresh_tokens_token_hash", "token_hash"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    device_info: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class UserApiKey(Base):
    """사용자 API 키 모델.

    외부 연동을 위한 API 키의 해시와 이름, 사용 이력 등을 저장합니다.
    """

    __tablename__ = "user_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")
