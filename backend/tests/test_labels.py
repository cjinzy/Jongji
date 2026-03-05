"""Label CRUD API 테스트 - TDD 방식.

라벨 생성/조회/수정/삭제, 프로젝트 내 이름 유일성을 검증합니다.
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
from jongji.models.label import Label
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
    """테스트용 AsyncClient 픽스처."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def owner_user(db_session) -> User:
    """프로젝트 소유자를 생성합니다."""
    user = User(
        email="label_owner@example.com",
        name="Label Owner",
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
    t = Team(name="Label Team", created_by=owner_user.id)
    db_session.add(t)
    await db_session.flush()
    member = TeamMember(team_id=t.id, user_id=owner_user.id, role=TeamRole.LEADER)
    db_session.add(member)
    await db_session.flush()
    await db_session.refresh(t)
    return t


@pytest.fixture
async def project(db_session, team, owner_user) -> Project:
    """테스트용 프로젝트를 생성합니다."""
    p = Project(
        team_id=team.id,
        name="Label Project",
        key="LBLPROJ",
        owner_id=owner_user.id,
    )
    db_session.add(p)
    await db_session.flush()
    pm = ProjectMember(project_id=p.id, user_id=owner_user.id, role=ProjectRole.LEADER)
    db_session.add(pm)
    await db_session.flush()
    await db_session.refresh(p)
    return p


@pytest.fixture
def owner_headers(owner_user: User) -> dict[str, str]:
    """소유자 인증 헤더를 반환합니다."""
    token = _make_token(str(owner_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def label(db_session, project) -> Label:
    """테스트용 라벨을 직접 생성합니다."""
    lb = Label(project_id=project.id, name="Bug", color="#FF0000")
    db_session.add(lb)
    await db_session.flush()
    await db_session.refresh(lb)
    return lb


class TestCreateLabel:
    """POST /api/v1/projects/{project_id}/labels 테스트."""

    async def test_create_label_success(self, client, owner_headers, project):
        """라벨을 생성할 수 있습니다."""
        resp = await client.post(
            f"/api/v1/projects/{project.id}/labels",
            headers=owner_headers,
            json={"name": "Feature", "color": "#00FF00"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Feature"
        assert data["color"] == "#00FF00"
        assert data["project_id"] == str(project.id)

    async def test_create_label_invalid_color(self, client, owner_headers, project):
        """유효하지 않은 색상 코드는 422를 반환합니다."""
        resp = await client.post(
            f"/api/v1/projects/{project.id}/labels",
            headers=owner_headers,
            json={"name": "Bad Color", "color": "red"},
        )
        assert resp.status_code == 422

    async def test_create_label_duplicate_name(self, client, owner_headers, project, label):
        """동일 프로젝트 내 중복 이름 라벨 생성은 409를 반환합니다."""
        resp = await client.post(
            f"/api/v1/projects/{project.id}/labels",
            headers=owner_headers,
            json={"name": "Bug", "color": "#0000FF"},
        )
        assert resp.status_code == 409

    async def test_create_label_unauthenticated(self, client, project):
        """인증 없이 라벨 생성 시 401을 반환합니다."""
        resp = await client.post(
            f"/api/v1/projects/{project.id}/labels",
            json={"name": "X", "color": "#123456"},
        )
        assert resp.status_code == 401


class TestListLabels:
    """GET /api/v1/projects/{project_id}/labels 테스트."""

    async def test_list_labels_success(self, client, owner_headers, project, label):
        """프로젝트의 라벨 목록을 조회할 수 있습니다."""
        resp = await client.get(
            f"/api/v1/projects/{project.id}/labels",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(lb["id"] == str(label.id) for lb in data)

    async def test_list_labels_empty(self, client, owner_headers, project):
        """라벨이 없으면 빈 목록을 반환합니다."""
        resp = await client.get(
            f"/api/v1/projects/{project.id}/labels",
            headers=owner_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestUpdateLabel:
    """PUT /api/v1/labels/{label_id} 테스트."""

    async def test_update_label_name(self, client, owner_headers, label):
        """라벨 이름을 수정할 수 있습니다."""
        resp = await client.put(
            f"/api/v1/labels/{label.id}",
            headers=owner_headers,
            json={"name": "Critical Bug"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Critical Bug"

    async def test_update_label_color(self, client, owner_headers, label):
        """라벨 색상을 수정할 수 있습니다."""
        resp = await client.put(
            f"/api/v1/labels/{label.id}",
            headers=owner_headers,
            json={"color": "#AABBCC"},
        )
        assert resp.status_code == 200
        assert resp.json()["color"] == "#AABBCC"

    async def test_update_label_not_found(self, client, owner_headers):
        """존재하지 않는 라벨 수정 시 404를 반환합니다."""
        import uuid
        resp = await client.put(
            f"/api/v1/labels/{uuid.uuid4()}",
            headers=owner_headers,
            json={"name": "X"},
        )
        assert resp.status_code == 404


class TestDeleteLabel:
    """DELETE /api/v1/labels/{label_id} 테스트."""

    async def test_delete_label_success(self, client, owner_headers, label):
        """라벨을 삭제할 수 있습니다 (204)."""
        resp = await client.delete(f"/api/v1/labels/{label.id}", headers=owner_headers)
        assert resp.status_code == 204

    async def test_delete_label_not_found(self, client, owner_headers):
        """존재하지 않는 라벨 삭제 시 404를 반환합니다."""
        import uuid
        resp = await client.delete(f"/api/v1/labels/{uuid.uuid4()}", headers=owner_headers)
        assert resp.status_code == 404

    async def test_label_gone_after_delete(self, client, owner_headers, project, label):
        """삭제 후 해당 라벨이 목록에서 사라져야 합니다."""
        await client.delete(f"/api/v1/labels/{label.id}", headers=owner_headers)
        resp = await client.get(f"/api/v1/projects/{project.id}/labels", headers=owner_headers)
        label_ids = [lb["id"] for lb in resp.json()]
        assert str(label.id) not in label_ids
