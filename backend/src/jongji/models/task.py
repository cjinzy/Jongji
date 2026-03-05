"""작업 관련 모델 (tasks, task_labels, task_tags, task_watchers, task_relations, task_comments, task_history, task_templates)."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jongji.database import Base
from jongji.models.enums import TaskStatus


class Task(Base):
    """작업 모델.

    프로젝트에 속한 개별 작업을 나타내며, 상태/우선순위/담당자/일정 등
    핵심 필드와 전문 검색용 tsvector를 포함합니다.
    """

    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "number"),
        CheckConstraint("priority >= 1 AND priority <= 9", name="ck_tasks_priority"),
        Index("idx_tasks_project_status", "project_id", "status", postgresql_where=text("NOT is_archived")),
        Index("idx_tasks_assignee_status", "assignee_id", "status", postgresql_where=text("NOT is_archived")),
        Index("idx_tasks_project_number", "project_id", "number"),
        Index("idx_tasks_search", "search_vector", postgresql_using="gin"),
        Index(
            "idx_tasks_trigram_title",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        ENUM(TaskStatus, name="taskstatus", create_type=True), default=TaskStatus.BACKLOG
    )
    priority: Mapped[int] = mapped_column(Integer, default=5)
    creator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    google_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    project: Mapped["Project"] = relationship(foreign_keys=[project_id])  # noqa: F821
    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])  # noqa: F821
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])  # noqa: F821
    labels: Mapped[list["TaskLabel"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    tags: Mapped[list["TaskTag"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    comments: Mapped[list["TaskComment"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    history: Mapped[list["TaskHistory"]] = relationship(back_populates="task", cascade="all, delete-orphan")


class TaskLabel(Base):
    """작업-라벨 연결 테이블.

    작업과 라벨 간의 N:M 관계를 관리합니다.
    """

    __tablename__ = "task_labels"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), primary_key=True)
    label_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("labels.id"), primary_key=True)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="labels")
    label: Mapped["Label"] = relationship(foreign_keys=[label_id])  # noqa: F821


class TaskTag(Base):
    """작업 태그 모델.

    작업에 자유 형식 태그를 부여합니다. 작업당 태그명은 고유합니다.
    """

    __tablename__ = "task_tags"
    __table_args__ = (
        UniqueConstraint("task_id", "tag"),
        Index("idx_task_tags_tag", "tag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    tag: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="tags")


class TaskWatcher(Base):
    """작업 감시자 연결 테이블.

    작업의 변경 알림을 받을 사용자를 관리합니다.
    """

    __tablename__ = "task_watchers"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)


class TaskRelation(Base):
    """작업 간 의존성 모델.

    한 작업이 다른 작업에 의해 차단되는 관계를 저장합니다.
    """

    __tablename__ = "task_relations"
    __table_args__ = (
        UniqueConstraint("task_id", "blocked_by_task_id"),
        Index("idx_task_relations_blocked", "blocked_by_task_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    blocked_by_task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class TaskComment(Base):
    """작업 댓글 모델.

    작업에 대한 사용자 댓글과 전문 검색 벡터를 저장합니다.
    """

    __tablename__ = "task_comments"
    __table_args__ = (
        Index("idx_comments_search", "search_vector", postgresql_using="gin"),
        Index(
            "idx_comments_trigram",
            "content",
            postgresql_using="gin",
            postgresql_ops={"content": "gin_trgm_ops"},
        ),
        Index("idx_task_comments_task", "task_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821


class TaskHistory(Base):
    """작업 변경 이력 모델.

    작업 필드의 변경 전후 값을 기록하여 감사 추적을 제공합니다.
    """

    __tablename__ = "task_history"
    __table_args__ = (Index("idx_task_history_task", "task_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    field: Mapped[str] = mapped_column(String, nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="history")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821


class TaskTemplate(Base):
    """작업 템플릿 모델.

    자주 사용하는 작업 패턴을 템플릿으로 저장하여 빠르게 생성할 수 있게 합니다.
    """

    __tablename__ = "task_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    title_template: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    project: Mapped["Project"] = relationship(foreign_keys=[project_id])  # noqa: F821
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])  # noqa: F821
