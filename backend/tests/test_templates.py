"""Task Template CRUD API 테스트 - TDD 방식.

템플릿 생성, 목록 조회, 수정, 삭제, 템플릿으로 작업 생성 엔드포인트를 테스트합니다.
ORM으로 직접 사용자를 생성하고 JWT를 발급하여 auth 의존성을 우회합니다.
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
async def tmpl_user(db_session) -> User:
    """테스트용 사용자를 ORM으로 생성합니다."""
    user = User(
        email=f"tmpluser_{uuid.uuid4().hex[:8]}@example.com",
        name="Template User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def tmpl_headers(tmpl_user) -> dict:
    """테스트용 인증 헤더."""
    token = _make_token(str(tmpl_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def tmpl_env(db_session, tmpl_user):
    """테스트용 팀/프로젝트 환경을 생성합니다."""
    team = Team(name="Template Team", created_by=tmpl_user.id)
    db_session.add(team)
    await db_session.flush()

    tm = TeamMember(team_id=team.id, user_id=tmpl_user.id, role=TeamRole.LEADER)
    db_session.add(tm)
    await db_session.flush()

    project = Project(
        team_id=team.id,
        name="Template Project",
        key=f"TMPL{uuid.uuid4().hex[:4].upper()}",
        owner_id=tmpl_user.id,
    )
    db_session.add(project)
    await db_session.flush()

    pm = ProjectMember(
        project_id=project.id,
        user_id=tmpl_user.id,
        role=ProjectRole.LEADER,
    )
    db_session.add(pm)
    await db_session.flush()

    return {"team": team, "project": project}


class TestCreateTemplate:
    """POST /api/v1/projects/{project_id}/templates 테스트."""

    async def test_create_template_success(self, client, tmpl_headers, tmpl_env):
        """템플릿 생성 성공 테스트."""
        resp = await client.post(
            f"/api/v1/projects/{tmpl_env['project'].id}/templates",
            json={
                "name": "Bug Report",
                "title_template": "Bug: {description}",
                "description": "Describe the bug",
                "priority": 3,
                "tags": ["bug", "urgent"],
            },
            headers=tmpl_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Bug Report"
        assert data["title_template"] == "Bug: {description}"
        assert data["priority"] == 3
        assert data["tags"] == ["bug", "urgent"]
        assert "id" in data

    async def test_create_template_minimal(self, client, tmpl_headers, tmpl_env):
        """최소 필드로 템플릿 생성 테스트."""
        resp = await client.post(
            f"/api/v1/projects/{tmpl_env['project'].id}/templates",
            json={
                "name": "Simple",
                "title_template": "Simple Task",
                "priority": 5,
            },
            headers=tmpl_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["description"] is None
        assert data["tags"] is None

    async def test_create_template_unauthenticated(self, client, tmpl_env):
        """인증 없이 템플릿 생성 시 401 테스트."""
        resp = await client.post(
            f"/api/v1/projects/{tmpl_env['project'].id}/templates",
            json={"name": "No Auth", "title_template": "T", "priority": 5},
        )
        assert resp.status_code == 401

    async def test_create_template_project_not_found(self, client, tmpl_headers):
        """존재하지 않는 프로젝트에 템플릿 생성 시 404 테스트."""
        resp = await client.post(
            f"/api/v1/projects/{uuid.uuid4()}/templates",
            json={"name": "No Project", "title_template": "T", "priority": 5},
            headers=tmpl_headers,
        )
        assert resp.status_code == 404


class TestListTemplates:
    """GET /api/v1/projects/{project_id}/templates 테스트."""

    async def test_list_templates_success(self, client, tmpl_headers, tmpl_env):
        """템플릿 목록 조회 테스트."""
        for i in range(3):
            await client.post(
                f"/api/v1/projects/{tmpl_env['project'].id}/templates",
                json={"name": f"Template {i}", "title_template": f"Task {i}", "priority": 5},
                headers=tmpl_headers,
            )
        resp = await client.get(
            f"/api/v1/projects/{tmpl_env['project'].id}/templates",
            headers=tmpl_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    async def test_list_templates_empty(self, client, tmpl_headers, tmpl_env):
        """빈 프로젝트의 템플릿 목록 조회 테스트."""
        resp = await client.get(
            f"/api/v1/projects/{tmpl_env['project'].id}/templates",
            headers=tmpl_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestUpdateTemplate:
    """PUT /api/v1/templates/{template_id} 테스트."""

    async def test_update_template_success(self, client, tmpl_headers, tmpl_env):
        """템플릿 수정 성공 테스트."""
        create_resp = await client.post(
            f"/api/v1/projects/{tmpl_env['project'].id}/templates",
            json={"name": "Old Name", "title_template": "Old Title", "priority": 5},
            headers=tmpl_headers,
        )
        template_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/templates/{template_id}",
            json={"name": "New Name", "priority": 1},
            headers=tmpl_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "New Name"
        assert data["priority"] == 1
        assert data["title_template"] == "Old Title"

    async def test_update_template_not_found(self, client, tmpl_headers):
        """존재하지 않는 템플릿 수정 시 404 테스트."""
        resp = await client.put(
            f"/api/v1/templates/{uuid.uuid4()}",
            json={"name": "Ghost"},
            headers=tmpl_headers,
        )
        assert resp.status_code == 404


class TestDeleteTemplate:
    """DELETE /api/v1/templates/{template_id} 테스트."""

    async def test_delete_template_success(self, client, tmpl_headers, tmpl_env):
        """템플릿 삭제 성공 테스트."""
        create_resp = await client.post(
            f"/api/v1/projects/{tmpl_env['project'].id}/templates",
            json={"name": "Delete Me", "title_template": "T", "priority": 5},
            headers=tmpl_headers,
        )
        template_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/templates/{template_id}",
            headers=tmpl_headers,
        )
        assert resp.status_code == 204

        # 삭제 후 목록에서 사라졌는지 확인
        list_resp = await client.get(
            f"/api/v1/projects/{tmpl_env['project'].id}/templates",
            headers=tmpl_headers,
        )
        ids = [t["id"] for t in list_resp.json()]
        assert template_id not in ids

    async def test_delete_template_not_found(self, client, tmpl_headers):
        """존재하지 않는 템플릿 삭제 시 404 테스트."""
        resp = await client.delete(
            f"/api/v1/templates/{uuid.uuid4()}",
            headers=tmpl_headers,
        )
        assert resp.status_code == 404


class TestCreateTaskFromTemplate:
    """POST /api/v1/templates/{template_id}/create-task 테스트."""

    async def test_create_task_from_template_success(self, client, tmpl_headers, tmpl_env):
        """템플릿으로 작업 생성 성공 테스트."""
        create_resp = await client.post(
            f"/api/v1/projects/{tmpl_env['project'].id}/templates",
            json={
                "name": "Feature Request",
                "title_template": "Feature: implement X",
                "description": "Implement this feature",
                "priority": 2,
                "tags": ["feature"],
            },
            headers=tmpl_headers,
        )
        template_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/templates/{template_id}/create-task",
            headers=tmpl_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Feature: implement X"
        assert data["description"] == "Implement this feature"
        assert data["priority"] == 2
        assert data["project_id"] == str(tmpl_env["project"].id)

    async def test_create_task_from_template_not_found(self, client, tmpl_headers):
        """존재하지 않는 템플릿으로 작업 생성 시 404 테스트."""
        resp = await client.post(
            f"/api/v1/templates/{uuid.uuid4()}/create-task",
            headers=tmpl_headers,
        )
        assert resp.status_code == 404
