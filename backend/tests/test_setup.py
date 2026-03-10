"""Setup Wizard API 엔드포인트 테스트 - TDD 방식.

초기 설정 마법사의 상태 확인, 관리자 생성, 설정 저장, 완료 처리를 검증합니다.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from jongji.config import settings
from jongji.main import app

TEST_SETUP_TOKEN = "test-setup-token-for-ci"


@pytest.fixture(autouse=True)
def _set_setup_token():
    """테스트 동안 SETUP_TOKEN 환경변수를 설정합니다."""
    original = settings.SETUP_TOKEN
    settings.SETUP_TOKEN = TEST_SETUP_TOKEN
    yield
    settings.SETUP_TOKEN = original


@pytest.fixture
async def client(db_session):
    """테스트용 HTTP 클라이언트.

    DB dependency를 테스트 세션으로 오버라이드합니다.

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


def _setup_headers() -> dict[str, str]:
    """Setup 토큰이 포함된 헤더를 반환합니다."""
    return {"Authorization": f"Bearer {TEST_SETUP_TOKEN}"}


class TestSetupStatus:
    """Setup 상태 확인 테스트."""

    async def test_setup_status_initial(self, client):
        """초기 상태에서 setup_completed=False 반환."""
        resp = await client.get("/api/v1/setup/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["setup_completed"] is False

    async def test_setup_status_oauth_available(self, client):
        """Google OAuth 설정 여부 확인."""
        resp = await client.get("/api/v1/setup/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "oauth_available" in data


class TestSetupAdmin:
    """Setup 관리자 생성 테스트."""

    async def test_create_admin_success(self, client):
        """정상적인 관리자 생성 시 201 반환."""
        resp = await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin@example.com",
                "password": "AdminPass123",
                "name": "Admin",
            },
            headers=_setup_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_admin"] is True
        assert data["email"] == "admin@example.com"

    async def test_create_admin_race_condition(self, client):
        """이미 사용자가 존재할 때 관리자 생성 시도 시 409 반환."""
        await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin1@example.com",
                "password": "AdminPass123",
                "name": "Admin1",
            },
            headers=_setup_headers(),
        )
        resp = await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin2@example.com",
                "password": "AdminPass123",
                "name": "Admin2",
            },
            headers=_setup_headers(),
        )
        assert resp.status_code == 409

    async def test_create_admin_short_password(self, client):
        """8자 미만 비밀번호로 관리자 생성 시 422 반환."""
        resp = await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin@example.com",
                "password": "short",
                "name": "Admin",
            },
            headers=_setup_headers(),
        )
        assert resp.status_code == 422

    async def test_create_admin_without_token(self, client):
        """Setup 토큰 없이 관리자 생성 시도 시 401 반환."""
        resp = await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin@example.com",
                "password": "AdminPass123",
                "name": "Admin",
            },
        )
        assert resp.status_code == 401

    async def test_create_admin_wrong_token(self, client):
        """잘못된 Setup 토큰으로 관리자 생성 시도 시 403 반환."""
        resp = await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin@example.com",
                "password": "AdminPass123",
                "name": "Admin",
            },
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 403


class TestSetupSettings:
    """Setup 설정 저장 테스트."""

    async def test_save_settings(self, client):
        """시스템 설정 저장 시 200 반환."""
        resp = await client.post(
            "/api/v1/setup/settings",
            json={
                "app_name": "MyApp",
                "timezone": "Asia/Seoul",
                "default_locale": "ko",
            },
            headers=_setup_headers(),
        )
        assert resp.status_code == 200

    async def test_save_settings_after_complete(self, client):
        """설정 완료 후 설정 저장 시 403 반환."""
        # 먼저 관리자 생성 + 설정 완료
        await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin@example.com",
                "password": "AdminPass123",
                "name": "Admin",
            },
            headers=_setup_headers(),
        )
        await client.post("/api/v1/setup/complete", headers=_setup_headers())
        # 완료 후 설정 변경 시도
        resp = await client.post(
            "/api/v1/setup/settings",
            json={"app_name": "Changed"},
            headers=_setup_headers(),
        )
        assert resp.status_code == 403


class TestSetupInit:
    """Setup init 원스텝 완료 테스트."""

    async def test_setup_init_success(self, client):
        """관리자 정보만으로 init 성공 시 201 반환."""
        resp = await client.post(
            "/api/v1/setup/init",
            json={
                "admin_name": "InitAdmin",
                "admin_email": "initadmin@example.com",
                "admin_password": "InitPass1",
                "app_name": "InitApp",
            },
        )
        assert resp.status_code == 201
        # 완료 상태 확인
        status_resp = await client.get("/api/v1/setup/status")
        assert status_resp.json()["setup_completed"] is True

    async def test_setup_init_with_oauth_fields(self, client):
        """OAuth 필드 포함 init 시 oauth_configured=True 반환."""
        resp = await client.post(
            "/api/v1/setup/init",
            json={
                "admin_name": "OAuthAdmin",
                "admin_email": "oauthinit@example.com",
                "admin_password": "OAuthPass1",
                "app_name": "OAuthApp",
                "google_client_id": "google-client-id-123",
                "google_client_secret": "google-secret-456",
                "google_redirect_uri": "http://localhost/auth/callback",
            },
        )
        assert resp.status_code == 201
        # oauth_configured 상태 확인
        status_resp = await client.get("/api/v1/setup/status")
        data = status_resp.json()
        assert data["setup_completed"] is True
        assert data["oauth_configured"] is True

    async def test_setup_init_without_oauth_fields(self, client):
        """OAuth 필드 없이 init 시 oauth_configured=False."""
        resp = await client.post(
            "/api/v1/setup/init",
            json={
                "admin_name": "NoOAuthAdmin",
                "admin_email": "nooauth@example.com",
                "admin_password": "NoOAuthPass1",
            },
        )
        assert resp.status_code == 201
        status_resp = await client.get("/api/v1/setup/status")
        data = status_resp.json()
        assert data["oauth_configured"] is False

    async def test_setup_init_already_completed_returns_403(self, client):
        """이미 완료된 setup에 재시도 시 403 반환."""
        payload = {
            "admin_name": "Admin",
            "admin_email": "dup@example.com",
            "admin_password": "DupPass1",
        }
        await client.post("/api/v1/setup/init", json=payload)
        resp = await client.post("/api/v1/setup/init", json=payload)
        assert resp.status_code == 403


class TestSetupComplete:
    """Setup 완료 처리 테스트."""

    async def test_complete_success(self, client):
        """관리자 존재 시 설정 완료 성공."""
        await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin@example.com",
                "password": "AdminPass123",
                "name": "Admin",
            },
            headers=_setup_headers(),
        )
        await client.post(
            "/api/v1/setup/settings",
            json={
                "app_name": "MyApp",
                "timezone": "Asia/Seoul",
            },
            headers=_setup_headers(),
        )
        resp = await client.post("/api/v1/setup/complete", headers=_setup_headers())
        assert resp.status_code == 200

        # 상태 확인
        status_resp = await client.get("/api/v1/setup/status")
        assert status_resp.json()["setup_completed"] is True

    async def test_complete_without_admin(self, client):
        """관리자 없이 설정 완료 시 400 반환."""
        resp = await client.post("/api/v1/setup/complete", headers=_setup_headers())
        assert resp.status_code == 400

    async def test_complete_already_completed(self, client):
        """이미 완료된 설정을 다시 완료 시도 시 409 반환."""
        await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin@example.com",
                "password": "AdminPass123",
                "name": "Admin",
            },
            headers=_setup_headers(),
        )
        await client.post("/api/v1/setup/complete", headers=_setup_headers())
        resp = await client.post("/api/v1/setup/complete", headers=_setup_headers())
        assert resp.status_code == 409
