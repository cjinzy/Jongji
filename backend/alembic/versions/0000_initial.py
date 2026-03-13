"""모든 기본 테이블 생성 (initial schema).

Revision ID: 0000
Revises:
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

# revision identifiers, used by Alembic.
revision = "0000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """모든 기본 테이블과 ENUM 타입, 인덱스, 제약 조건을 생성합니다."""
    # --- ENUM 타입: 모델의 create_type=True가 metadata를 통해 자동 생성 ---
    # env.py에서 모델 import 시 metadata에 등록되어, alembic 연결 시점에 이미 생성됨
    taskstatus = sa.Enum(
        "BACKLOG", "TODO", "PROGRESS", "REVIEW", "DONE", "REOPEN", "CLOSED",
        name="taskstatus", create_type=False,
    )
    teamrole = sa.Enum("leader", "member", name="teamrole", create_type=False)
    projectrole = sa.Enum("leader", "member", name="projectrole", create_type=False)
    alertchannel = sa.Enum(
        "email", "telegram", "discord", "google_chat", "slack",
        name="alertchannel", create_type=False,
    )
    alertlogstatus = sa.Enum("pending", "sent", "failed", name="alertlogstatus", create_type=False)
    auditloglevel = sa.Enum("minimal", "standard", "full", name="auditloglevel", create_type=False)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("password_hash", sa.String, nullable=True),
        sa.Column("google_id", sa.String, unique=True, nullable=True),
        sa.Column("avatar_url", sa.String, nullable=True),
        sa.Column("is_admin", sa.Boolean, server_default="false"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("locale", sa.String, server_default="ko"),
        sa.Column("timezone", sa.String, nullable=True),
        sa.Column("daily_summary_time", sa.Time, server_default="00:00:00"),
        sa.Column("onboarding_completed", sa.Boolean, server_default="false"),
        sa.Column("dnd_start", sa.Time, nullable=True),
        sa.Column("dnd_end", sa.Time, nullable=True),
        sa.Column("passkey_credential", sa.JSON, nullable=True),
        sa.Column("totp_secret", sa.String, nullable=True),
        sa.Column("login_fail_count", sa.Integer, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # --- refresh_tokens ---
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("device_info", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    # --- user_api_keys ---
    op.create_table(
        "user_api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("key_hash", sa.String, nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # --- teams ---
    op.create_table(
        "teams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("slug", sa.String, nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_archived", sa.Boolean, server_default="false"),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_teams_slug", "teams", ["slug"], unique=True)

    # --- team_members ---
    op.create_table(
        "team_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "team_id",
            UUID(as_uuid=True),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("role", teamrole, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("team_id", "user_id"),
    )
    op.create_index("idx_team_members_user_id", "team_members", ["user_id"])

    # --- team_invites ---
    op.create_table(
        "team_invites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "team_id",
            UUID(as_uuid=True),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("token", sa.String, unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("use_count", sa.Integer, server_default="0"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_team_invites_token",
        "team_invites",
        ["token"],
        postgresql_where=sa.text("is_active = TRUE"),
    )

    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "team_id",
            UUID(as_uuid=True),
            sa.ForeignKey("teams.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("slug", sa.String, nullable=False),
        sa.Column("key", sa.String, unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_private", sa.Boolean, server_default="false"),
        sa.Column("is_archived", sa.Boolean, server_default="false"),
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("task_counter", sa.Integer, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("team_id", "slug", name="uq_projects_team_slug"),
    )
    op.create_index("idx_projects_team_id", "projects", ["team_id"])
    op.create_index("ix_projects_slug", "projects", ["slug"])

    # --- project_members ---
    op.create_table(
        "project_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("role", projectrole, nullable=False),
        sa.Column("min_alert_priority", sa.Integer, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("project_id", "user_id"),
    )

    # --- labels ---
    op.create_table(
        "labels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("color", sa.String, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("project_id", "name"),
    )

    # --- tasks (WITHOUT search_vector — added in 0001) ---
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", taskstatus, server_default="BACKLOG"),
        sa.Column("priority", sa.Integer, server_default="5"),
        sa.Column(
            "creator_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "assignee_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("is_archived", sa.Boolean, server_default="false"),
        sa.Column("google_event_id", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("project_id", "number"),
        sa.CheckConstraint(
            "priority >= 1 AND priority <= 9", name="ck_tasks_priority"
        ),
    )
    op.create_index(
        "idx_tasks_project_status",
        "tasks",
        ["project_id", "status"],
        postgresql_where=sa.text("NOT is_archived"),
    )
    op.create_index(
        "idx_tasks_assignee_status",
        "tasks",
        ["assignee_id", "status"],
        postgresql_where=sa.text("NOT is_archived"),
    )
    op.create_index("idx_tasks_project_number", "tasks", ["project_id", "number"])

    # --- task_labels ---
    op.create_table(
        "task_labels",
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            primary_key=True,
        ),
        sa.Column(
            "label_id",
            UUID(as_uuid=True),
            sa.ForeignKey("labels.id"),
            primary_key=True,
        ),
    )

    # --- task_tags ---
    op.create_table(
        "task_tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column("tag", sa.String, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("task_id", "tag"),
    )
    op.create_index("idx_task_tags_tag", "task_tags", ["tag"])

    # --- task_watchers ---
    op.create_table(
        "task_watchers",
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
    )

    # --- task_relations ---
    op.create_table(
        "task_relations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "blocked_by_task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("task_id", "blocked_by_task_id"),
    )
    op.create_index(
        "idx_task_relations_blocked", "task_relations", ["blocked_by_task_id"]
    )

    # --- task_comments (WITHOUT search_vector — added in 0001) ---
    op.create_table(
        "task_comments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_task_comments_task", "task_comments", ["task_id", "created_at"]
    )

    # --- task_history ---
    op.create_table(
        "task_history",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("field", sa.String, nullable=False),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_task_history_task", "task_history", ["task_id", "created_at"]
    )

    # --- task_templates ---
    op.create_table(
        "task_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("title_template", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("priority", sa.Integer, nullable=False),
        sa.Column("tags", ARRAY(sa.Text), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # --- attachments ---
    op.create_table(
        "attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=True,
        ),
        sa.Column(
            "comment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("task_comments.id"),
            nullable=True,
        ),
        sa.Column("filename", sa.String, nullable=False),
        sa.Column("storage_path", sa.String, nullable=False),
        sa.Column("content_type", sa.String, nullable=False),
        sa.Column("size", sa.BigInteger, nullable=False),
        sa.Column(
            "uploaded_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("is_temp", sa.Boolean, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_attachments_temp",
        "attachments",
        ["is_temp", "created_at"],
        postgresql_where=sa.text("is_temp = TRUE"),
    )

    # --- alert_configs ---
    op.create_table(
        "alert_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("channel", alertchannel, nullable=False),
        sa.Column("is_enabled", sa.Boolean, server_default="true"),
        sa.Column("webhook_url", sa.String, nullable=True),
        sa.Column("chat_id", sa.String, nullable=True),
        sa.Column("config_json", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "channel"),
    )

    # --- alert_logs ---
    op.create_table(
        "alert_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String, nullable=True),
        sa.Column("channel", sa.String, nullable=False),
        sa.Column("status", alertlogstatus, server_default="pending"),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_alert_logs_pending",
        "alert_logs",
        ["status", "created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("resource_type", sa.String, nullable=False),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("ip_address", sa.String, nullable=True),
        sa.Column("log_level", auditloglevel, nullable=False),
        sa.Column("source", sa.String, server_default="api"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_audit_logs_created", "audit_logs", ["created_at"])

    # --- system_settings ---
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String, primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    """모든 테이블과 ENUM 타입을 역순으로 삭제합니다."""
    op.drop_table("system_settings")
    op.drop_table("audit_logs")
    op.drop_table("alert_logs")
    op.drop_table("alert_configs")
    op.drop_table("attachments")
    op.drop_table("task_templates")
    op.drop_table("task_history")
    op.drop_table("task_comments")
    op.drop_table("task_relations")
    op.drop_table("task_watchers")
    op.drop_table("task_tags")
    op.drop_table("task_labels")
    op.drop_table("tasks")
    op.drop_table("labels")
    op.drop_table("project_members")
    op.drop_table("projects")
    op.drop_table("team_invites")
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("user_api_keys")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

    # ENUM 타입 삭제
    sa.Enum(name="auditloglevel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="alertlogstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="alertchannel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="projectrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="teamrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="taskstatus").drop(op.get_bind(), checkfirst=True)
