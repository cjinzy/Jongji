"""알림 관련 모델 (alert_configs, alert_logs)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jongji.database import Base
from jongji.models.enums import AlertChannel, AlertLogStatus


class AlertConfig(Base):
    """알림 설정 모델.

    사용자별 알림 채널 설정(webhook URL, chat ID 등)을 저장합니다.
    사용자당 채널별로 하나의 설정만 허용합니다.
    """

    __tablename__ = "alert_configs"
    __table_args__ = (UniqueConstraint("user_id", "channel"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    channel: Mapped[AlertChannel] = mapped_column(
        ENUM(AlertChannel, name="alertchannel", create_type=True), nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    webhook_url: Mapped[str | None] = mapped_column(String, nullable=True)
    chat_id: Mapped[str | None] = mapped_column(String, nullable=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821


class AlertLog(Base):
    """알림 발송 로그 모델.

    발송 시도, 재시도 횟수, 성공/실패 상태, 에러 메시지 등을 기록합니다.
    """

    __tablename__ = "alert_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    event_type: Mapped[str | None] = mapped_column(String, nullable=True)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[AlertLogStatus] = mapped_column(
        ENUM(AlertLogStatus, name="alertlogstatus", create_type=True), default=AlertLogStatus.PENDING
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # Relationships
    user: Mapped["User"] = relationship(foreign_keys=[user_id])  # noqa: F821


# ENUM 컬럼을 직접 비교해야 asyncpg에서 타입 캐스팅이 올바르게 처리됨
Index(
    "idx_alert_logs_pending",
    AlertLog.status,
    AlertLog.created_at,
    postgresql_where=(AlertLog.status == AlertLogStatus.PENDING),
)
