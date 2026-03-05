"""라벨 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from jongji.database import Base


class Label(Base):
    """프로젝트별 라벨 모델.

    작업에 부여할 수 있는 색상이 있는 라벨을 관리합니다.
    프로젝트 내에서 이름이 고유해야 합니다.
    """

    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
