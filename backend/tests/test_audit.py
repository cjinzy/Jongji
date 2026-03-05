"""감사 로그 API 엔드포인트 테스트.

GET /api/v1/audit-logs 엔드포인트의 인증/권한 및 필터 동작을 검증합니다.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from jongji.main import app
from jongji.models.team import Team, TeamMember
from jongji.models.user import User
from jongji.services.audit_service import log_action


@pytest.fixture
async def client(db_session):
    """테스트용 HTTP 클라이언트.

    Args:
        db_session: 테스트용 DB 세션 픽스처.

    Yields:
        AsyncClient: 비동기 HTTP 클라이언트.
    """
    from jongji.database import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _register_and_login(client, email: str, name: str = "Test") -> str:
    """회원가입 후 액세스 토큰을 반환하는 헬퍼.

    Args:
        client: 비동기 HTTP 클라이언트.
        email: 사용자 이메일.
        name: 사용자 이름.

    Returns:
        JWT 액세스 토큰 문자열.
    """
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "name": name},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    return resp.json()["access_token"]


async def _make_leader(db_session, user_email: str) -> None:
    """사용자를 팀 리더로 만드는 헬퍼.

    Args:
        db_session: 비동기 DB 세션.
        user_email: 사용자 이메일.
    """
    from sqlalchemy import select

    result = await db_session.execute(select(User).where(User.email == user_email))
    user = result.scalar_one()

    team = Team(name="Test Team", created_by=user.id)
    db_session.add(team)
    await db_session.flush()

    membership = TeamMember(team_id=team.id, user_id=user.id, role="leader")
    db_session.add(membership)
    await db_session.flush()


class TestAuditLogList:
    """GET /api/v1/audit-logs 엔드포인트 테스트."""

    async def test_unauthenticated_returns_401(self, client):
        """인증 없이 요청 시 401을 반환해야 한다."""
        resp = await client.get("/api/v1/audit-logs")
        assert resp.status_code == 401

    async def test_non_leader_returns_403(self, client, db_session):
        """팀 리더가 아닌 일반 멤버는 403을 반환해야 한다."""
        token = await _register_and_login(client, "member_audit@example.com", "Member")
        resp = await client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_team_leader_can_access(self, client, db_session):
        """팀 리더는 200과 목록을 반환해야 한다."""
        token = await _register_and_login(client, "leader_audit@example.com", "Leader")
        await _make_leader(db_session, "leader_audit@example.com")

        resp = await client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_admin_can_access(self, client, db_session):
        """관리자는 팀 리더 여부 상관없이 200을 반환해야 한다."""
        from sqlalchemy import select

        token = await _register_and_login(client, "admin_audit@example.com", "Admin")
        result = await db_session.execute(select(User).where(User.email == "admin_audit@example.com"))
        user = result.scalar_one()
        user.is_admin = True
        await db_session.flush()

        resp = await client.get(
            "/api/v1/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_filter_by_action(self, client, db_session):
        """action 필터로 특정 액션만 조회할 수 있어야 한다."""
        from sqlalchemy import select

        token = await _register_and_login(client, "filter_audit@example.com", "Filter")
        result = await db_session.execute(select(User).where(User.email == "filter_audit@example.com"))
        user = result.scalar_one()
        user.is_admin = True
        await db_session.flush()

        await log_action(
            db_session,
            user_id=user.id,
            action="task.create",
            resource_type="task",
            detail={"title": "test"},
            source="api",
        )
        await log_action(
            db_session,
            user_id=user.id,
            action="task.delete",
            resource_type="task",
            source="api",
        )
        await db_session.flush()

        resp = await client.get(
            "/api/v1/audit-logs",
            params={"action": "task.create"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["action"] == "task.create" for item in data["items"])

    async def test_pagination(self, client, db_session):
        """limit/offset 파라미터로 페이지네이션이 동작해야 한다."""
        from sqlalchemy import select

        token = await _register_and_login(client, "page_audit@example.com", "Page")
        result = await db_session.execute(select(User).where(User.email == "page_audit@example.com"))
        user = result.scalar_one()
        user.is_admin = True
        await db_session.flush()

        resp = await client.get(
            "/api/v1/audit-logs",
            params={"limit": 5, "offset": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["items"]) <= 5
