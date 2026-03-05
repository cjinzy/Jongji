"""Export API 테스트.

프로젝트/업무 JSON 및 Markdown export 엔드포인트를 테스트합니다.
ORM으로 직접 데이터를 생성하고 JWT를 발급하여 auth 의존성을 우회합니다.
"""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from jongji.config import settings
from jongji.database import get_db
from jongji.main import app
from jongji.models.enums import ProjectRole, TeamRole
from jongji.models.project import Project, ProjectMember
from jongji.models.task import Task, TaskComment
from jongji.models.team import Team, TeamMember
from jongji.models.user import User


def _hash_password(password: str) -> str:
    """테스트용 비밀번호 해싱."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _make_token(user_id: str) -> str:
    """테스트용 JWT 액세스 토큰을 생성합니다."""
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@pytest.fixture
async def client(db_session):
    """테스트용 AsyncClient 픽스처."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def export_user(db_session) -> User:
    """테스트용 사용자를 ORM으로 생성합니다."""
    user = User(
        email="exportuser@example.com",
        name="Export User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def export_headers(export_user) -> dict:
    """테스트용 인증 헤더."""
    token = _make_token(str(export_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def export_env(db_session, export_user):
    """테스트용 팀/프로젝트/업무 환경을 생성합니다."""
    team = Team(name="Export Team", created_by=export_user.id)
    db_session.add(team)
    await db_session.flush()

    tm = TeamMember(team_id=team.id, user_id=export_user.id, role=TeamRole.LEADER)
    db_session.add(tm)
    await db_session.flush()

    project = Project(
        team_id=team.id,
        name="Export Project",
        key="EXP",
        owner_id=export_user.id,
    )
    db_session.add(project)
    await db_session.flush()

    pm = ProjectMember(
        project_id=project.id,
        user_id=export_user.id,
        role=ProjectRole.LEADER,
    )
    db_session.add(pm)
    await db_session.flush()

    from jongji.models.enums import TaskStatus

    task = Task(
        project_id=project.id,
        number=1,
        title="Export Task",
        description="Task description for export",
        status=TaskStatus.BACKLOG,
        priority=3,
        creator_id=export_user.id,
    )
    db_session.add(task)
    await db_session.flush()

    comment = TaskComment(
        task_id=task.id,
        user_id=export_user.id,
        content="Test comment",
    )
    db_session.add(comment)
    await db_session.flush()

    return {"team": team, "project": project, "task": task, "comment": comment}


class TestExportProject:
    """GET /api/v1/projects/{project_id}/export 테스트."""

    async def test_export_project_json(self, client, export_headers, export_env):
        """프로젝트 JSON export 테스트."""
        project_id = export_env["project"].id
        resp = await client.get(
            f"/api/v1/projects/{project_id}/export?format=json",
            headers=export_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Export Project"
        assert data["key"] == "EXP"
        assert "tasks" in data
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["title"] == "Export Task"
        assert "labels" in data

    async def test_export_project_markdown(self, client, export_headers, export_env):
        """프로젝트 Markdown export 테스트."""
        project_id = export_env["project"].id
        resp = await client.get(
            f"/api/v1/projects/{project_id}/export?format=markdown",
            headers=export_headers,
        )
        assert resp.status_code == 200
        content = resp.text
        assert "# Export Project (EXP)" in content
        assert "Export Task" in content

    async def test_export_project_default_format(self, client, export_headers, export_env):
        """format 미지정 시 JSON export 테스트."""
        project_id = export_env["project"].id
        resp = await client.get(
            f"/api/v1/projects/{project_id}/export",
            headers=export_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data

    async def test_export_project_not_found(self, client, export_headers):
        """존재하지 않는 프로젝트 export 시 404 테스트."""
        resp = await client.get(
            f"/api/v1/projects/{uuid.uuid4()}/export",
            headers=export_headers,
        )
        assert resp.status_code == 404

    async def test_export_project_unauthenticated(self, client, export_env):
        """인증 없이 export 시 401 테스트."""
        project_id = export_env["project"].id
        resp = await client.get(f"/api/v1/projects/{project_id}/export")
        assert resp.status_code == 401


class TestExportTask:
    """GET /api/v1/tasks/{task_id}/export 테스트."""

    async def test_export_task_json(self, client, export_headers, export_env):
        """업무 JSON export 테스트."""
        task_id = export_env["task"].id
        resp = await client.get(
            f"/api/v1/tasks/{task_id}/export?format=json",
            headers=export_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Export Task"
        assert data["description"] == "Task description for export"
        assert data["priority"] == 3
        assert "comments" in data
        assert len(data["comments"]) == 1
        assert data["comments"][0]["content"] == "Test comment"
        assert "history" in data
        assert "labels" in data

    async def test_export_task_markdown(self, client, export_headers, export_env):
        """업무 Markdown export 테스트."""
        task_id = export_env["task"].id
        resp = await client.get(
            f"/api/v1/tasks/{task_id}/export?format=markdown",
            headers=export_headers,
        )
        assert resp.status_code == 200
        content = resp.text
        assert "Export Task" in content
        assert "Task description for export" in content
        assert "Test comment" in content

    async def test_export_task_not_found(self, client, export_headers):
        """존재하지 않는 업무 export 시 404 테스트."""
        resp = await client.get(
            f"/api/v1/tasks/{uuid.uuid4()}/export",
            headers=export_headers,
        )
        assert resp.status_code == 404

    async def test_export_task_unauthenticated(self, client, export_env):
        """인증 없이 업무 export 시 401 테스트."""
        task_id = export_env["task"].id
        resp = await client.get(f"/api/v1/tasks/{task_id}/export")
        assert resp.status_code == 401
