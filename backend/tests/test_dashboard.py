"""Dashboard API 테스트.

프로젝트 대시보드 집계 엔드포인트의 성공/인증 실패/404 시나리오를 검증합니다.
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
from jongji.models.enums import ProjectRole, TaskStatus, TeamRole
from jongji.models.project import Project, ProjectMember
from jongji.models.task import Task
from jongji.models.team import Team, TeamMember
from jongji.models.user import User


def _hash_password(password: str) -> str:
    """테스트용 비밀번호 해싱."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _make_token(user_id: str) -> str:
    """테스트용 JWT 액세스 토큰을 생성합니다.

    Args:
        user_id: 사용자 UUID 문자열.

    Returns:
        JWT 토큰 문자열.
    """
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@pytest.fixture
async def client(db_session):
    """테스트용 AsyncClient 픽스처.

    get_db를 db_session으로 오버라이드합니다.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def owner_user(db_session) -> User:
    """프로젝트 소유자를 ORM으로 직접 생성합니다."""
    user = User(
        email="dashboard_owner@example.com",
        name="Dashboard Owner",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def team(db_session, owner_user) -> Team:
    """테스트용 팀을 생성합니다."""
    t = Team(name="Dashboard Team", created_by=owner_user.id)
    db_session.add(t)
    await db_session.flush()
    member = TeamMember(team_id=t.id, user_id=owner_user.id, role=TeamRole.LEADER)
    db_session.add(member)
    await db_session.flush()
    await db_session.refresh(t)
    return t


@pytest.fixture
async def project(db_session, team, owner_user) -> Project:
    """테스트용 프로젝트를 직접 생성합니다."""
    p = Project(
        team_id=team.id,
        name="Dashboard Project",
        key="DASHPROJ",
        description="Dashboard test project",
        is_private=False,
        owner_id=owner_user.id,
    )
    db_session.add(p)
    await db_session.flush()
    member = ProjectMember(project_id=p.id, user_id=owner_user.id, role=ProjectRole.LEADER)
    db_session.add(member)
    await db_session.flush()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def tasks(db_session, project, owner_user) -> list[Task]:
    """테스트용 업무를 여러 상태로 생성합니다."""
    task_list = []
    statuses = [TaskStatus.TODO, TaskStatus.TODO, TaskStatus.PROGRESS, TaskStatus.DONE, TaskStatus.CLOSED]
    for i, s in enumerate(statuses):
        task = Task(
            project_id=project.id,
            number=i + 1,
            title=f"Task {i + 1}",
            status=s,
            priority=i + 1,
            creator_id=owner_user.id,
            assignee_id=owner_user.id if s not in {TaskStatus.DONE, TaskStatus.CLOSED} else None,
        )
        db_session.add(task)
        task_list.append(task)
    await db_session.flush()
    return task_list


@pytest.fixture
def owner_headers(owner_user: User) -> dict[str, str]:
    """소유자 인증 헤더를 반환합니다."""
    token = _make_token(str(owner_user.id))
    return {"Authorization": f"Bearer {token}"}


class TestGetDashboard:
    """GET /api/v1/projects/{project_id}/dashboard 테스트."""

    async def test_dashboard_success(self, client, owner_headers, project, tasks):
        """인증된 사용자가 대시보드 집계 데이터를 조회할 수 있습니다."""
        resp = await client.get(
            f"/api/v1/projects/{project.id}/dashboard",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()

        # 필수 필드 존재 확인
        assert "status_counts" in data
        assert "priority_distribution" in data
        assert "assignee_workload" in data
        assert "daily_created" in data
        assert "daily_completed" in data
        assert "label_distribution" in data
        assert "total_tasks" in data
        assert "completed_tasks" in data
        assert "completion_rate" in data

        # 집계 값 검증
        assert data["total_tasks"] == len(tasks)
        assert data["completed_tasks"] == 2  # DONE + CLOSED
        assert 0.0 <= data["completion_rate"] <= 1.0

        # 상태 키 확인
        sc = data["status_counts"]
        assert "TODO" in sc
        assert sc["TODO"] == 2
        assert sc["DONE"] == 1
        assert sc["CLOSED"] == 1

    async def test_dashboard_empty_project(self, client, owner_headers, project):
        """업무가 없는 프로젝트의 대시보드는 0 값들을 반환합니다."""
        resp = await client.get(
            f"/api/v1/projects/{project.id}/dashboard",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tasks"] == 0
        assert data["completed_tasks"] == 0
        assert data["completion_rate"] == 0.0
        assert data["assignee_workload"] == []
        assert data["label_distribution"] == []

    async def test_dashboard_unauthenticated(self, client, project):
        """인증 없이 대시보드에 접근하면 401을 반환합니다."""
        resp = await client.get(f"/api/v1/projects/{project.id}/dashboard")
        assert resp.status_code == 401

    async def test_dashboard_project_not_found(self, client, owner_headers):
        """존재하지 않는 프로젝트의 대시보드를 조회하면 404를 반환합니다."""
        nonexistent_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/projects/{nonexistent_id}/dashboard",
            headers=owner_headers,
        )
        assert resp.status_code == 404
