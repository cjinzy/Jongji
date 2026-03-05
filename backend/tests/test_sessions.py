"""세션 관리 API 엔드포인트 테스트.

GET /api/v1/sessions 및 DELETE /api/v1/sessions/{session_id} 엔드포인트를 검증합니다.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from jongji.main import app


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


async def _register_and_login(client, email: str, name: str = "Test") -> tuple[str, str]:
    """회원가입 후 (access_token, refresh_token) 반환 헬퍼.

    Args:
        client: 비동기 HTTP 클라이언트.
        email: 사용자 이메일.
        name: 사용자 이름.

    Returns:
        (액세스 토큰, 리프레시 토큰 쿠키 값) 튜플.
    """
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "name": name},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    access_token = resp.json()["access_token"]
    refresh_token = resp.cookies.get("refresh_token", "")
    return access_token, refresh_token


class TestListSessions:
    """GET /api/v1/sessions 엔드포인트 테스트."""

    async def test_unauthenticated_returns_401(self, client):
        """인증 없이 요청 시 401을 반환해야 한다."""
        resp = await client.get("/api/v1/sessions")
        assert resp.status_code == 401

    async def test_authenticated_returns_session_list(self, client):
        """로그인 후 세션 목록을 조회할 수 있어야 한다."""
        token, _ = await _register_and_login(client, "session_list@example.com", "SessionList")
        resp = await client.get(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    async def test_session_has_required_fields(self, client):
        """세션 응답에 필수 필드가 포함되어야 한다."""
        token, _ = await _register_and_login(client, "session_fields@example.com", "SessionFields")
        resp = await client.get(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        session = items[0]
        assert "id" in session
        assert "created_at" in session
        assert "is_current" in session


class TestRevokeSession:
    """DELETE /api/v1/sessions/{session_id} 엔드포인트 테스트."""

    async def test_unauthenticated_returns_401(self, client):
        """인증 없이 요청 시 401을 반환해야 한다."""
        import uuid

        resp = await client.delete(f"/api/v1/sessions/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_revoke_own_session(self, client):
        """자신의 세션을 revoke할 수 있어야 한다."""
        token, _ = await _register_and_login(client, "revoke_session@example.com", "Revoke")

        # 세션 목록에서 ID 가져오기
        list_resp = await client.get(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        items = list_resp.json()["items"]
        assert len(items) >= 1
        session_id = items[0]["id"]

        resp = await client.delete(
            f"/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_revoke_nonexistent_session_returns_404(self, client):
        """존재하지 않는 세션 revoke 시 404를 반환해야 한다."""
        import uuid

        token, _ = await _register_and_login(client, "revoke_404@example.com", "Revoke404")
        resp = await client.delete(
            f"/api/v1/sessions/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_cannot_revoke_other_users_session(self, client):
        """다른 사용자의 세션은 revoke할 수 없어야 한다."""
        token_a, _ = await _register_and_login(client, "user_a_sessions@example.com", "UserA")
        token_b, _ = await _register_and_login(client, "user_b_sessions@example.com", "UserB")

        # A의 세션 목록 조회
        list_resp = await client.get(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        items = list_resp.json()["items"]
        session_id_a = items[0]["id"]

        # B가 A의 세션을 revoke 시도
        resp = await client.delete(
            f"/api/v1/sessions/{session_id_a}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert resp.status_code == 404
