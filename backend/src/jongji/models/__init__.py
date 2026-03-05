"""SQLAlchemy 모델 패키지.

모든 모델을 import하여 Alembic이 자동으로 테이블을 감지할 수 있게 합니다.
"""

from jongji.database import Base
from jongji.models.alert import AlertConfig, AlertLog
from jongji.models.attachment import Attachment
from jongji.models.audit import AuditLog
from jongji.models.enums import (
    AlertChannel,
    AlertLogStatus,
    AuditLogLevel,
    ProjectRole,
    TaskStatus,
    TeamRole,
)
from jongji.models.label import Label
from jongji.models.project import Project, ProjectMember
from jongji.models.system import SystemSetting
from jongji.models.task import (
    Task,
    TaskComment,
    TaskHistory,
    TaskLabel,
    TaskRelation,
    TaskTag,
    TaskTemplate,
    TaskWatcher,
)
from jongji.models.team import Team, TeamInvite, TeamMember
from jongji.models.user import RefreshToken, User, UserApiKey

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "UserApiKey",
    "Team",
    "TeamMember",
    "TeamInvite",
    "Project",
    "ProjectMember",
    "Task",
    "TaskLabel",
    "TaskTag",
    "TaskWatcher",
    "TaskRelation",
    "TaskComment",
    "TaskHistory",
    "TaskTemplate",
    "Label",
    "Attachment",
    "AlertConfig",
    "AlertLog",
    "AuditLog",
    "SystemSetting",
    "TaskStatus",
    "TeamRole",
    "ProjectRole",
    "AlertChannel",
    "AlertLogStatus",
    "AuditLogLevel",
]
