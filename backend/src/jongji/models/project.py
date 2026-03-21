"""프로젝트 관련 모델 (projects, project_members)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jongji.database import Base
from jongji.models.enums import ProjectRole
from jongji.utils.slug import generate_slug


class Project(Base):
    """프로젝트 모델.

    팀에 속한 프로젝트를 나타내며, 고유 키와 작업 카운터를 관리합니다.
    slug는 name에서 자동 생성됩니다.
    """

    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("team_id", "slug", name="uq_projects_team_slug"),
        Index("idx_projects_team_id", "team_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, index=True, default="")
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_counter: Mapped[int] = mapped_column(Integer, default=0)
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
    team: Mapped["Team"] = relationship(foreign_keys=[team_id])  # noqa: F821
    owner: Mapped["User"] = relationship(foreign_keys=[owner_id])  # noqa: F821
    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    """프로젝트 멤버 모델.

    프로젝트와 사용자 간의 N:M 관계를 역할 및 최소 알림 우선순위와 함께 관리합니다.
    """

    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[ProjectRole] = mapped_column(
        ENUM(ProjectRole, name="projectrole", create_type=True, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    min_alert_priority: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821
