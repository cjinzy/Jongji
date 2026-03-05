"""Project CRUD API 테스트 - TDD 방식.

프로젝트 생성/조회/수정/아카이브, 멤버 관리, key 영구 점유를 검증합니다.
ORM으로 직접 객체를 생성하고 JWT를 발급하여 auth 의존성을 우회합니다.
"""

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
    """프로젝트 소유자 사용자를 ORM으로 직접 생성합니다."""
    user = User(
        email="owner@example.com",
        name="Owner User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session) -> User:
    """다른 사용자를 ORM으로 직접 생성합니다."""
    user = User(
        email="other@example.com",
        name="Other User",
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
    t = Team(name="Test Team", created_by=owner_user.id)
    db_session.add(t)
    await db_session.flush()
    # owner를 팀 리더로 추가
    member = TeamMember(team_id=t.id, user_id=owner_user.id, role=TeamRole.LEADER)
    db_session.add(member)
    await db_session.flush()
    await db_session.refresh(t)
    return t


@pytest.fixture
async def team_with_other(db_session, team, other_user) -> Team:
    """other_user도 팀 멤버로 등록된 팀 픽스처."""
    member = TeamMember(team_id=team.id, user_id=other_user.id, role=TeamRole.MEMBER)
    db_session.add(member)
    await db_session.flush()
    return team


@pytest.fixture
def owner_headers(owner_user: User) -> dict[str, str]:
    """소유자 인증 헤더를 반환합니다."""
    token = _make_token(str(owner_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_headers(other_user: User) -> dict[str, str]:
    """다른 사용자 인증 헤더를 반환합니다."""
    token = _make_token(str(other_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def project(db_session, team, owner_user) -> Project:
    """테스트용 프로젝트를 직접 생성합니다."""
    p = Project(
        team_id=team.id,
        name="Test Project",
        key="TESTPROJ",
        description="A test project",
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


class TestCreateProject:
    """POST /api/v1/projects 테스트."""

    async def test_create_project_success(self, client, owner_headers, team):
        """팀 멤버가 프로젝트를 생성할 수 있습니다."""
        resp = await client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "My Project",
                "key": "MYPROJ",
                "team_id": str(team.id),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Project"
        assert data["key"] == "MYPROJ"
        assert data["team_id"] == str(team.id)
        assert data["is_archived"] is False

    async def test_create_project_invalid_key_format(self, client, owner_headers, team):
        """key가 패턴에 맞지 않으면 422를 반환합니다."""
        resp = await client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "My Project",
                "key": "my-proj",  # 소문자 포함 - 유효하지 않음
                "team_id": str(team.id),
            },
        )
        assert resp.status_code == 422

    async def test_create_project_duplicate_key(self, client, owner_headers, team, project):
        """이미 존재하는 key로 프로젝트를 생성하면 409를 반환합니다."""
        resp = await client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "Another Project",
                "key": "TESTPROJ",  # 이미 사용 중인 key
                "team_id": str(team.id),
            },
        )
        assert resp.status_code == 409

    async def test_create_project_archived_key_still_occupied(self, client, owner_headers, team, project, db_session):
        """아카이브된 프로젝트의 key도 영구 점유됩니다."""
        # 프로젝트를 아카이브
        project.is_archived = True
        await db_session.flush()

        # 동일한 key로 새 프로젝트 생성 시도
        resp = await client.post(
            "/api/v1/projects",
            headers=owner_headers,
            json={
                "name": "Reuse Key Project",
                "key": "TESTPROJ",
                "team_id": str(team.id),
            },
        )
        assert resp.status_code == 409

    async def test_create_project_unauthenticated(self, client, team):
        """인증 없이 프로젝트를 생성하면 401을 반환합니다."""
        resp = await client.post(
            "/api/v1/projects",
            json={"name": "X", "key": "XPROJ", "team_id": str(team.id)},
        )
        assert resp.status_code == 401


class TestListProjects:
    """GET /api/v1/projects 테스트."""

    async def test_list_projects_by_team(self, client, owner_headers, team, project):
        """팀 ID로 프로젝트 목록을 조회할 수 있습니다."""
        resp = await client.get(
            "/api/v1/projects",
            headers=owner_headers,
            params={"team_id": str(team.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(p["id"] == str(project.id) for p in data)

    async def test_list_projects_excludes_archived(self, client, owner_headers, team, project, db_session):
        """아카이브된 프로젝트는 목록에서 제외됩니다."""
        project.is_archived = True
        await db_session.flush()

        resp = await client.get(
            "/api/v1/projects",
            headers=owner_headers,
            params={"team_id": str(team.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert not any(p["id"] == str(project.id) for p in data)


class TestGetProject:
    """GET /api/v1/projects/{project_id} 테스트."""

    async def test_get_project_success(self, client, owner_headers, project):
        """프로젝트 상세 정보를 조회할 수 있습니다."""
        resp = await client.get(f"/api/v1/projects/{project.id}", headers=owner_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(project.id)
        assert data["name"] == "Test Project"

    async def test_get_project_not_found(self, client, owner_headers):
        """존재하지 않는 프로젝트 조회 시 404를 반환합니다."""
        import uuid
        resp = await client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=owner_headers)
        assert resp.status_code == 404


class TestUpdateProject:
    """PUT /api/v1/projects/{project_id} 테스트."""

    async def test_update_project_success(self, client, owner_headers, project):
        """소유자가 프로젝트를 수정할 수 있습니다."""
        resp = await client.put(
            f"/api/v1/projects/{project.id}",
            headers=owner_headers,
            json={"name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    async def test_update_project_description(self, client, owner_headers, project):
        """설명을 수정할 수 있습니다."""
        resp = await client.put(
            f"/api/v1/projects/{project.id}",
            headers=owner_headers,
            json={"description": "New description"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "New description"


class TestArchiveProject:
    """DELETE /api/v1/projects/{project_id} 테스트."""

    async def test_archive_project_success(self, client, owner_headers, project):
        """소유자가 프로젝트를 아카이브할 수 있습니다 (204)."""
        resp = await client.delete(f"/api/v1/projects/{project.id}", headers=owner_headers)
        assert resp.status_code == 204

    async def test_archive_project_key_still_in_db(self, client, owner_headers, project, db_session):
        """아카이브 후 key가 DB에서 유지됩니다."""
        await client.delete(f"/api/v1/projects/{project.id}", headers=owner_headers)
        await db_session.refresh(project)
        assert project.is_archived is True
        assert project.key == "TESTPROJ"


class TestProjectMembers:
    """프로젝트 멤버 관리 테스트."""

    async def test_get_members(self, client, owner_headers, project, owner_user):
        """프로젝트 멤버 목록을 조회할 수 있습니다."""
        resp = await client.get(f"/api/v1/projects/{project.id}/members", headers=owner_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(m["user_id"] == str(owner_user.id) for m in data)

    async def test_add_member(self, client, owner_headers, team_with_other, project, other_user):
        """팀 멤버를 프로젝트에 추가할 수 있습니다."""
        resp = await client.post(
            f"/api/v1/projects/{project.id}/members",
            headers=owner_headers,
            json={"user_id": str(other_user.id), "role": "member"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == str(other_user.id)
        assert data["role"] == "member"

    async def test_add_member_not_team_member(self, client, owner_headers, project, other_user):
        """팀 멤버가 아닌 사용자는 프로젝트에 추가할 수 없습니다 (400)."""
        resp = await client.post(
            f"/api/v1/projects/{project.id}/members",
            headers=owner_headers,
            json={"user_id": str(other_user.id), "role": "member"},
        )
        assert resp.status_code == 400

    async def test_remove_member(self, client, owner_headers, team_with_other, project, other_user, db_session):
        """프로젝트 멤버를 제거할 수 있습니다."""
        # 먼저 멤버 추가
        pm = ProjectMember(project_id=project.id, user_id=other_user.id, role=ProjectRole.MEMBER)
        db_session.add(pm)
        await db_session.flush()

        resp = await client.delete(
            f"/api/v1/projects/{project.id}/members/{other_user.id}",
            headers=owner_headers,
        )
        assert resp.status_code == 204
