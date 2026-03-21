"""감사 로그 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jongji.database import Base
from jongji.models.enums import AuditLogLevel


class AuditLog(Base):
    """감사 로그 모델.

    사용자 행동과 시스템 이벤트를 기록하며, 리소스 유형/ID,
    IP 주소, 로그 레벨 등 상세 정보를 저장합니다.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (Index("idx_audit_logs_created", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    resource_type: Mapped[str] = mapped_column(String, nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    log_level: Mapped[AuditLogLevel] = mapped_column(
        ENUM(AuditLogLevel, name="auditloglevel", create_type=True, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String, default="api")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    user: Mapped["User | None"] = relationship(foreign_keys=[user_id])  # noqa: F821
