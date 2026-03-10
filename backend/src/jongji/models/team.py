"""팀 관련 모델 (teams, team_members, team_invites)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jongji.database import Base
from jongji.models.enums import TeamRole
from jongji.utils.slug import generate_slug


class Team(Base):
    """팀 모델.

    프로젝트를 그룹화하는 조직 단위로, 생성자와 보관 상태를 관리합니다.
    slug는 name에서 자동 생성됩니다.
    """

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __init__(self, **kwargs):
        """slug가 제공되지 않으면 name에서 자동 생성합니다."""
        if "slug" not in kwargs and "name" in kwargs:
            kwargs["slug"] = generate_slug(kwargs["name"])
        super().__init__(**kwargs)

    # Relationships
    members: Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")
    invites: Mapped[list["TeamInvite"]] = relationship(back_populates="team", cascade="all, delete-orphan")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])  # noqa: F821


class TeamMember(Base):
    """팀 멤버 모델.

    팀과 사용자 간의 N:M 관계를 역할(leader/member)과 함께 관리합니다.
    """

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id"),
        Index("idx_team_members_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[TeamRole] = mapped_column(ENUM(TeamRole, name="teamrole", create_type=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821


class TeamInvite(Base):
    """팀 초대 링크 모델.

    고유 토큰 기반의 팀 초대를 관리하며, 만료 시간과 사용 횟수를 추적합니다.
    """

    __tablename__ = "team_invites"
    __table_args__ = (
        Index("idx_team_invites_token", "token", postgresql_where=text("is_active = TRUE")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="invites")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])  # noqa: F821
