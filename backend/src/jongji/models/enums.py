"""모델에서 사용하는 PostgreSQL ENUM 타입 정의."""

import enum


class TaskStatus(enum.StrEnum):
    """작업 상태를 나타내는 열거형."""

    BACKLOG = "BACKLOG"
    TODO = "TODO"
    PROGRESS = "PROGRESS"
    REVIEW = "REVIEW"
    DONE = "DONE"
    REOPEN = "REOPEN"
    CLOSED = "CLOSED"


class TeamRole(enum.StrEnum):
    """팀 내 역할을 나타내는 열거형."""

    LEADER = "leader"
    MEMBER = "member"


class ProjectRole(enum.StrEnum):
    """프로젝트 내 역할을 나타내는 열거형."""

    LEADER = "leader"
    MEMBER = "member"


class AlertChannel(enum.StrEnum):
    """알림 채널 유형을 나타내는 열거형."""

    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    GOOGLE_CHAT = "google_chat"
    SLACK = "slack"


class AlertLogStatus(enum.StrEnum):
    """알림 로그 상태를 나타내는 열거형."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class AuditLogLevel(enum.StrEnum):
    """감사 로그 수준을 나타내는 열거형."""

    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"
