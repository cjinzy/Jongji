"""Task CRUD API 테스트 - TDD 방식.

작업 생성, 조회, 수정, 삭제, 복제 엔드포인트를 테스트합니다.
ORM으로 직접 사용자를 생성하고 JWT를 발급하여 auth 의존성을 우회합니다.
"""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from jongji.config import settings
from jongji.database import get_db
from jongji.main import app
from jongji.models.enums import ProjectRole, TaskStatus, TeamRole
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
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
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
async def task_user(db_session) -> User:
    """테스트용 사용자를 ORM으로 생성합니다."""
    user = User(
        email="taskuser@example.com",
        name="Task User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def task_headers(task_user) -> dict:
    """테스트용 인증 헤더."""
    token = _make_token(str(task_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def task_env(db_session, task_user):
    """테스트용 팀/프로젝트 환경을 생성합니다."""
    team = Team(name="Task Team", created_by=task_user.id)
    db_session.add(team)
    await db_session.flush()

    tm = TeamMember(team_id=team.id, user_id=task_user.id, role=TeamRole.LEADER)
    db_session.add(tm)
    await db_session.flush()

    project = Project(
        team_id=team.id,
        name="Task Project",
        key="TASK",
        owner_id=task_user.id,
    )
    db_session.add(project)
    await db_session.flush()

    pm = ProjectMember(
        project_id=project.id,
        user_id=task_user.id,
        role=ProjectRole.LEADER,
    )
    db_session.add(pm)
    await db_session.flush()

    return {"team": team, "project": project}


class TestCreateTask:
    """POST /api/v1/projects/{project_id}/tasks 테스트."""

    async def test_create_task_success(self, client, task_headers, task_env):
        """작업 생성 테스트."""
        resp = await client.post(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            json={"title": "Test Task", "priority": 3},
            headers=task_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Task"
        assert data["priority"] == 3
        assert data["number"] == 1
        assert data["status"] == TaskStatus.BACKLOG.value

    async def test_create_task_auto_increment(self, client, task_headers, task_env):
        """작업 번호 자동 증가 테스트."""
        resp1 = await client.post(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            json={"title": "Task 1"},
            headers=task_headers,
        )
        resp2 = await client.post(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            json={"title": "Task 2"},
            headers=task_headers,
        )
        assert resp1.json()["number"] == 1
        assert resp2.json()["number"] == 2

    async def test_create_task_unauthenticated(self, client, task_env):
        """인증 없이 작업 생성 시 401 테스트."""
        resp = await client.post(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            json={"title": "No Auth"},
        )
        assert resp.status_code == 401


class TestGetTask:
    """GET /api/v1/tasks/{task_id} 테스트."""

    async def test_get_task_success(self, client, task_headers, task_env):
        """작업 상세 조회 테스트."""
        create_resp = await client.post(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            json={"title": "Get Me"},
            headers=task_headers,
        )
        task_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/tasks/{task_id}", headers=task_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Get Me"

    async def test_get_task_not_found(self, client, task_headers):
        """존재하지 않는 작업 조회 시 404 테스트."""
        resp = await client.get(f"/api/v1/tasks/{uuid.uuid4()}", headers=task_headers)
        assert resp.status_code == 404


class TestUpdateTask:
    """PUT /api/v1/tasks/{task_id} 테스트."""

    async def test_update_task_success(self, client, task_headers, task_env):
        """작업 수정 테스트."""
        create_resp = await client.post(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            json={"title": "Old Title"},
            headers=task_headers,
        )
        task_id = create_resp.json()["id"]
        resp = await client.put(
            f"/api/v1/tasks/{task_id}",
            json={"title": "New Title", "priority": 1},
            headers=task_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"
        assert resp.json()["priority"] == 1


class TestArchiveTask:
    """DELETE /api/v1/tasks/{task_id} 테스트."""

    async def test_archive_task_success(self, client, task_headers, task_env):
        """작업 보관 처리 테스트."""
        create_resp = await client.post(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            json={"title": "Archive Me"},
            headers=task_headers,
        )
        task_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/v1/tasks/{task_id}", headers=task_headers)
        assert resp.status_code == 204


class TestCloneTask:
    """POST /api/v1/tasks/{task_id}/clone 테스트."""

    async def test_clone_task_success(self, client, task_headers, task_env):
        """작업 복제 테스트."""
        create_resp = await client.post(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            json={"title": "Clone Me", "priority": 2},
            headers=task_headers,
        )
        task_id = create_resp.json()["id"]
        resp = await client.post(f"/api/v1/tasks/{task_id}/clone", headers=task_headers)
        assert resp.status_code == 201
        cloned = resp.json()
        assert cloned["title"] == "Clone Me"
        assert cloned["priority"] == 2
        assert cloned["id"] != task_id


class TestListTasks:
    """GET /api/v1/projects/{project_id}/tasks 테스트."""

    async def test_list_tasks_success(self, client, task_headers, task_env):
        """작업 목록 조회 테스트."""
        for i in range(3):
            await client.post(
                f"/api/v1/projects/{task_env['project'].id}/tasks",
                json={"title": f"Task {i}"},
                headers=task_headers,
            )
        resp = await client.get(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            headers=task_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 3
        assert data["has_more"] is False

    async def test_list_tasks_empty(self, client, task_headers, task_env):
        """빈 프로젝트의 작업 목록 조회 테스트."""
        resp = await client.get(
            f"/api/v1/projects/{task_env['project'].id}/tasks",
            headers=task_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 0
