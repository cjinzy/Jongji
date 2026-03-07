"""Admin OAuth API 엔드포인트 테스트.

GET/PUT/DELETE /api/v1/admin/oauth/google 엔드포인트와 접근 제어를 검증합니다.
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


@pytest.fixture
async def admin_token(client):
    """관리자 계정 생성 후 액세스 토큰을 반환합니다.

    Args:
        client: 테스트용 HTTP 클라이언트.

    Returns:
        str: 관리자 액세스 토큰.
    """
    # setup/init으로 관리자 생성
    resp = await client.post(
        "/api/v1/setup/init",
        json={
            "admin_name": "Admin",
            "admin_email": "oauthadmin@example.com",
            "admin_password": "AdminPass1",
            "app_name": "TestApp",
        },
    )
    assert resp.status_code == 201

    # 로그인
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "oauthadmin@example.com",
            "password": "AdminPass1",
        },
    )
    assert login_resp.status_code == 200
    return login_resp.json()["access_token"]


@pytest.fixture
async def user_token(client):
    """일반 사용자 계정 생성 후 액세스 토큰을 반환합니다.

    Args:
        client: 테스트용 HTTP 클라이언트.

    Returns:
        str: 일반 사용자 액세스 토큰.
    """
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "normaluser@example.com",
            "password": "UserPass1",
            "name": "Normal User",
        },
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


class TestAdminOAuthGet:
    """GET /api/v1/admin/oauth/google 테스트."""

    async def test_get_oauth_not_configured_returns_404(self, client, admin_token):
        """OAuth 미설정 시 404 반환."""
        resp = await client.get(
            "/api/v1/admin/oauth/google",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_get_oauth_masked_after_save(self, client, admin_token):
        """설정 저장 후 조회 시 시크릿이 마스킹되어 반환됨."""
        # 설정 저장
        put_resp = await client.put(
            "/api/v1/admin/oauth/google",
            json={
                "client_id": "test-client-id",
                "client_secret": "super-secret-value",
                "redirect_uri": "http://localhost/callback",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert put_resp.status_code == 200

        # 조회
        get_resp = await client.get(
            "/api/v1/admin/oauth/google",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["client_id"] == "test-client-id"
        # 시크릿은 마스킹되어야 함 — 원문 노출 금지
        assert "super-secret-value" not in data.get("client_secret_masked", "")
        assert "****" in data.get("client_secret_masked", "")
        assert data["redirect_uri"] == "http://localhost/callback"
        assert data["is_configured"] is True


class TestAdminOAuthPut:
    """PUT /api/v1/admin/oauth/google 테스트."""

    async def test_put_oauth_settings_success(self, client, admin_token):
        """유효한 데이터로 설정 저장 시 200 + 마스킹된 응답 반환."""
        resp = await client.put(
            "/api/v1/admin/oauth/google",
            json={
                "client_id": "new-client-id",
                "client_secret": "new-secret",
                "redirect_uri": "https://app.example.com/auth/callback",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["client_id"] == "new-client-id"
        assert data["is_configured"] is True

    async def test_put_oauth_missing_field_returns_422(self, client, admin_token):
        """필수 필드 누락 시 422 반환."""
        resp = await client.put(
            "/api/v1/admin/oauth/google",
            json={
                "client_id": "only-id",
                # client_secret, redirect_uri 누락
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422


class TestAdminOAuthDelete:
    """DELETE /api/v1/admin/oauth/google 테스트."""

    async def test_delete_oauth_success(self, client, admin_token):
        """설정 삭제 성공 시 204 반환."""
        # 먼저 설정 저장
        await client.put(
            "/api/v1/admin/oauth/google",
            json={
                "client_id": "del-client-id",
                "client_secret": "del-secret",
                "redirect_uri": "http://localhost/del",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # 삭제
        del_resp = await client.delete(
            "/api/v1/admin/oauth/google",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert del_resp.status_code == 204

        # 삭제 후 조회 시 404
        get_resp = await client.get(
            "/api/v1/admin/oauth/google",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_resp.status_code == 404

    async def test_delete_oauth_not_configured_returns_404(self, client, admin_token):
        """미설정 상태에서 삭제 시 404 반환."""
        resp = await client.delete(
            "/api/v1/admin/oauth/google",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404


class TestAdminOAuthAccessControl:
    """OAuth 엔드포인트 접근 제어 테스트."""

    async def test_non_admin_get_forbidden(self, client, user_token):
        """일반 사용자가 OAuth 설정 조회 시 403 반환."""
        resp = await client.get(
            "/api/v1/admin/oauth/google",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    async def test_non_admin_put_forbidden(self, client, user_token):
        """일반 사용자가 OAuth 설정 저장 시 403 반환."""
        resp = await client.put(
            "/api/v1/admin/oauth/google",
            json={
                "client_id": "x",
                "client_secret": "y",
                "redirect_uri": "http://z",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    async def test_non_admin_delete_forbidden(self, client, user_token):
        """일반 사용자가 OAuth 설정 삭제 시 403 반환."""
        resp = await client.delete(
            "/api/v1/admin/oauth/google",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_get_unauthorized(self, client):
        """미인증 요청 시 401 반환."""
        resp = await client.get("/api/v1/admin/oauth/google")
        assert resp.status_code == 401
