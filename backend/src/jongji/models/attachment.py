"""첨부파일 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jongji.database import Base


class Attachment(Base):
    """첨부파일 모델.

    작업 또는 댓글에 첨부된 파일의 메타데이터를 저장합니다.
    임시 파일 관리를 위한 is_temp 플래그를 포함합니다.
    """

    __tablename__ = "attachments"
    __table_args__ = (
        Index("idx_attachments_temp", "is_temp", "created_at", postgresql_where=text("is_temp = TRUE")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    comment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("task_comments.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_temp: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    uploader: Mapped["User"] = relationship(foreign_keys=[uploaded_by])  # noqa: F821
