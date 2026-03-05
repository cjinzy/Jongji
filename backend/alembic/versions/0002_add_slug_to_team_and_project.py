"""add slug to team and project.

3단계 마이그레이션:
1. nullable=True로 slug 컬럼 추가
2. 기존 데이터에 name 기반 slug 생성
3. nullable=False로 변경 + 인덱스/제약조건 추가

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-05
"""

import re
import unicodedata

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _generate_slug(name: str) -> str:
    """이름에서 URL-safe slug를 생성합니다."""
    slug = unicodedata.normalize("NFC", name.strip().lower())
    slug = re.sub(r"[^\w가-힣-]", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug or "untitled"


def upgrade() -> None:
    """slug 컬럼을 teams, projects 테이블에 추가합니다."""
    # Step 1: nullable=True로 컬럼 추가
    op.add_column("teams", sa.Column("slug", sa.String(), nullable=True))
    op.add_column("projects", sa.Column("slug", sa.String(), nullable=True))

    # Step 2: 기존 데이터에 slug 생성
    conn = op.get_bind()

    # teams slug 생성
    teams = conn.execute(sa.text("SELECT id, name FROM teams")).fetchall()
    used_team_slugs: set[str] = set()
    for team_id, name in teams:
        base_slug = _generate_slug(name)
        slug = base_slug
        suffix = 0
        while slug in used_team_slugs:
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        used_team_slugs.add(slug)
        conn.execute(
            sa.text("UPDATE teams SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": team_id},
        )

    # projects slug 생성 (팀 내 유니크)
    projects = conn.execute(
        sa.text("SELECT id, team_id, name FROM projects")
    ).fetchall()
    used_project_slugs: dict[str, set[str]] = {}  # team_id -> set of slugs
    for project_id, team_id, name in projects:
        team_key = str(team_id)
        if team_key not in used_project_slugs:
            used_project_slugs[team_key] = set()
        base_slug = _generate_slug(name)
        slug = base_slug
        suffix = 0
        while slug in used_project_slugs[team_key]:
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        used_project_slugs[team_key].add(slug)
        conn.execute(
            sa.text("UPDATE projects SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": project_id},
        )

    # Step 3: nullable=False로 변경 + 인덱스/제약조건 추가
    op.alter_column("teams", "slug", nullable=False)
    op.alter_column("projects", "slug", nullable=False)

    op.create_index(op.f("ix_teams_slug"), "teams", ["slug"], unique=True)
    op.create_index(op.f("ix_projects_slug"), "projects", ["slug"], unique=False)
    op.create_unique_constraint("uq_projects_team_slug", "projects", ["team_id", "slug"])


def downgrade() -> None:
    """slug 컬럼 및 관련 인덱스/제약조건을 제거합니다."""
    op.drop_constraint("uq_projects_team_slug", "projects", type_="unique")
    op.drop_index(op.f("ix_projects_slug"), table_name="projects")
    op.drop_index(op.f("ix_teams_slug"), table_name="teams")
    op.drop_column("projects", "slug")
    op.drop_column("teams", "slug")
