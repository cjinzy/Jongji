"""Team CRUD API 테스트 - TDD 방식.

팀 생성/조회/수정/아카이브, 멤버 관리, 역할/권한을 검증합니다.
ORM으로 직접 사용자를 생성하고 JWT를 발급하여 auth 의존성을 우회합니다.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from jongji.config import settings
from jongji.database import get_db
from jongji.main import app
from jongji.models.enums import TeamRole
from jongji.models.project import Project
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
async def leader_user(db_session) -> User:
    """팀 리더 사용자를 ORM으로 직접 생성합니다."""
    user = User(
        email="leader@example.com",
        name="Leader User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def member_user(db_session) -> User:
    """일반 멤버 사용자를 ORM으로 직접 생성합니다."""
    user = User(
        email="member@example.com",
        name="Member User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def another_user(db_session) -> User:
    """팀 외부 사용자를 ORM으로 직접 생성합니다."""
    user = User(
        email="another@example.com",
        name="Another User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session) -> User:
    """관리자 사용자를 ORM으로 직접 생성합니다."""
    user = User(
        email="admin_team@example.com",
        name="Admin User",
        password_hash=_hash_password("adminpass123"),
        is_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
def leader_headers(leader_user: User) -> dict[str, str]:
    """리더 인증 헤더를 반환합니다."""
    token = _make_token(str(leader_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def member_headers(member_user: User) -> dict[str, str]:
    """멤버 인증 헤더를 반환합니다."""
    token = _make_token(str(member_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def another_headers(another_user: User) -> dict[str, str]:
    """외부 사용자 인증 헤더를 반환합니다."""
    token = _make_token(str(another_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    """관리자 인증 헤더를 반환합니다."""
    token = _make_token(str(admin_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def existing_team(db_session, leader_user: User) -> Team:
    """테스트용 팀과 리더 멤버십을 ORM으로 직접 생성합니다."""
    team = Team(
        name="Test Team",
        description="Test team description",
        created_by=leader_user.id,
    )
    db_session.add(team)
    await db_session.flush()

    membership = TeamMember(
        team_id=team.id,
        user_id=leader_user.id,
        role=TeamRole.LEADER,
    )
    db_session.add(membership)
    await db_session.flush()
    await db_session.refresh(team)
    return team


@pytest.fixture
async def team_with_member(db_session, existing_team: Team, member_user: User) -> Team:
    """멤버가 포함된 팀 픽스처."""
    membership = TeamMember(
        team_id=existing_team.id,
        user_id=member_user.id,
        role=TeamRole.MEMBER,
    )
    db_session.add(membership)
    await db_session.flush()
    return existing_team


class TestCreateTeam:
    """POST /api/v1/teams 테스트."""

    async def test_create_team(self, client, leader_headers, leader_user):
        """팀을 생성하면 201이 반환되고 생성자가 리더로 등록됩니다."""
        resp = await client.post(
            "/api/v1/teams",
            headers=leader_headers,
            json={"name": "My New Team", "description": "A great team"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My New Team"
        assert data["description"] == "A great team"
        assert data["is_archived"] is False
        assert UUID(data["created_by"]) == leader_user.id
        assert data["member_count"] == 1

    async def test_create_team_no_description(self, client, leader_headers):
        """description 없이도 팀을 생성할 수 있습니다."""
        resp = await client.post(
            "/api/v1/teams",
            headers=leader_headers,
            json={"name": "Minimal Team"},
        )
        assert resp.status_code == 201
        assert resp.json()["description"] is None

    async def test_create_team_unauthenticated(self, client):
        """인증 없이 팀 생성 시 401이 반환됩니다."""
        resp = await client.post(
            "/api/v1/teams",
            json={"name": "Fail Team"},
        )
        assert resp.status_code == 401


class TestListTeams:
    """GET /api/v1/teams 테스트."""

    async def test_list_teams(self, client, leader_headers, existing_team, leader_user):
        """사용자가 속한 팀 목록만 반환됩니다."""
        resp = await client.get("/api/v1/teams", headers=leader_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(t["id"] == str(existing_team.id) for t in data)

    async def test_list_teams_excludes_others(self, client, another_headers, existing_team):
        """다른 팀에 속하지 않은 사용자에게는 해당 팀이 보이지 않습니다."""
        resp = await client.get("/api/v1/teams", headers=another_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert not any(t["id"] == str(existing_team.id) for t in data)

    async def test_list_teams_excludes_archived(self, client, db_session, leader_headers, existing_team):
        """아카이브된 팀은 목록에서 제외됩니다."""
        existing_team.is_archived = True
        db_session.add(existing_team)
        await db_session.flush()

        resp = await client.get("/api/v1/teams", headers=leader_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert not any(t["id"] == str(existing_team.id) for t in data)


class TestGetTeam:
    """GET /api/v1/teams/{team_id} 테스트."""

    async def test_get_team(self, client, leader_headers, existing_team):
        """팀 상세 정보를 조회할 수 있습니다."""
        resp = await client.get(f"/api/v1/teams/{existing_team.id}", headers=leader_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(existing_team.id)
        assert data["name"] == "Test Team"

    async def test_get_team_not_found(self, client, leader_headers):
        """존재하지 않는 팀 조회 시 404가 반환됩니다."""
        import uuid
        resp = await client.get(f"/api/v1/teams/{uuid.uuid4()}", headers=leader_headers)
        assert resp.status_code == 404

    async def test_get_team_unauthenticated(self, client, existing_team):
        """인증 없이 팀 조회 시 401이 반환됩니다."""
        resp = await client.get(f"/api/v1/teams/{existing_team.id}")
        assert resp.status_code == 401


class TestUpdateTeam:
    """PUT /api/v1/teams/{team_id} 테스트."""

    async def test_update_team(self, client, leader_headers, existing_team):
        """팀 리더가 팀 정보를 수정할 수 있습니다."""
        resp = await client.put(
            f"/api/v1/teams/{existing_team.id}",
            headers=leader_headers,
            json={"name": "Updated Team Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Team Name"

    async def test_update_team_forbidden(self, client, member_headers, team_with_member):
        """일반 멤버는 팀 정보를 수정할 수 없습니다 (403)."""
        resp = await client.put(
            f"/api/v1/teams/{team_with_member.id}",
            headers=member_headers,
            json={"name": "Should Fail"},
        )
        assert resp.status_code == 403

    async def test_update_team_by_admin(self, client, admin_headers, existing_team):
        """관리자는 리더가 아니어도 팀 정보를 수정할 수 있습니다."""
        resp = await client.put(
            f"/api/v1/teams/{existing_team.id}",
            headers=admin_headers,
            json={"name": "Admin Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Admin Updated"

    async def test_update_team_non_member_forbidden(self, client, another_headers, existing_team):
        """팀 외부 사용자는 팀 정보를 수정할 수 없습니다 (403)."""
        resp = await client.put(
            f"/api/v1/teams/{existing_team.id}",
            headers=another_headers,
            json={"name": "Should Fail"},
        )
        assert resp.status_code == 403


class TestArchiveTeam:
    """DELETE /api/v1/teams/{team_id} 테스트."""

    async def test_archive_team(self, client, leader_headers, existing_team, db_session):
        """팀 리더가 팀을 아카이브하면 204가 반환됩니다."""
        resp = await client.delete(
            f"/api/v1/teams/{existing_team.id}",
            headers=leader_headers,
        )
        assert resp.status_code == 204

        await db_session.refresh(existing_team)
        assert existing_team.is_archived is True

    async def test_archive_cascades_projects(
        self, client, leader_headers, existing_team, db_session, leader_user
    ):
        """팀 아카이브 시 해당 팀의 모든 프로젝트도 아카이브됩니다."""
        project = Project(
            team_id=existing_team.id,
            name="Team Project",
            key="TP",
            owner_id=leader_user.id,
        )
        db_session.add(project)
        await db_session.flush()
        await db_session.refresh(project)

        resp = await client.delete(
            f"/api/v1/teams/{existing_team.id}",
            headers=leader_headers,
        )
        assert resp.status_code == 204

        await db_session.refresh(project)
        assert project.is_archived is True

    async def test_archive_team_forbidden_member(self, client, member_headers, team_with_member):
        """일반 멤버는 팀을 아카이브할 수 없습니다 (403)."""
        resp = await client.delete(
            f"/api/v1/teams/{team_with_member.id}",
            headers=member_headers,
        )
        assert resp.status_code == 403

    async def test_archive_team_forbidden_non_member(self, client, another_headers, existing_team):
        """팀 외부 사용자는 팀을 아카이브할 수 없습니다 (403)."""
        resp = await client.delete(
            f"/api/v1/teams/{existing_team.id}",
            headers=another_headers,
        )
        assert resp.status_code == 403


class TestTeamMembers:
    """팀 멤버 관리 테스트."""

    async def test_get_members(self, client, leader_headers, existing_team):
        """팀 멤버 목록을 조회할 수 있습니다."""
        resp = await client.get(
            f"/api/v1/teams/{existing_team.id}/members",
            headers=leader_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_add_member(self, client, leader_headers, existing_team, member_user):
        """리더가 새 멤버를 팀에 추가할 수 있습니다."""
        resp = await client.post(
            f"/api/v1/teams/{existing_team.id}/members",
            headers=leader_headers,
            json={"user_id": str(member_user.id), "role": "member"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert UUID(data["user_id"]) == member_user.id
        assert data["role"] == "member"

    async def test_add_member_forbidden(self, client, member_headers, team_with_member, another_user):
        """일반 멤버는 다른 사용자를 팀에 추가할 수 없습니다 (403)."""
        resp = await client.post(
            f"/api/v1/teams/{team_with_member.id}/members",
            headers=member_headers,
            json={"user_id": str(another_user.id), "role": "member"},
        )
        assert resp.status_code == 403

    async def test_remove_member(self, client, leader_headers, team_with_member, member_user):
        """리더가 멤버를 팀에서 제거할 수 있습니다."""
        resp = await client.delete(
            f"/api/v1/teams/{team_with_member.id}/members/{member_user.id}",
            headers=leader_headers,
        )
        assert resp.status_code == 204

    async def test_remove_member_forbidden(self, client, member_headers, team_with_member, another_user):
        """일반 멤버는 다른 멤버를 제거할 수 없습니다 (403)."""
        # 먼저 another_user를 팀에 추가 (직접 ORM)
        resp = await client.delete(
            f"/api/v1/teams/{team_with_member.id}/members/{another_user.id}",
            headers=member_headers,
        )
        assert resp.status_code == 403

    async def test_add_member_returns_user_info(self, client, leader_headers, existing_team, member_user):
        """멤버 추가 응답에 사용자 이름과 이메일이 포함됩니다."""
        resp = await client.post(
            f"/api/v1/teams/{existing_team.id}/members",
            headers=leader_headers,
            json={"user_id": str(member_user.id), "role": "member"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_name"] == member_user.name
        assert data["user_email"] == member_user.email
