"""시스템 설정 모델."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from jongji.database import Base


class SystemSetting(Base):
    """시스템 전역 설정 모델.

    키-값 쌍으로 시스템 설정을 저장합니다 (예: setup_completed, maintenance_mode 등).
    """

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
