"""Setup Wizard API 엔드포인트 테스트 - TDD 방식.

초기 설정 마법사의 상태 확인, 관리자 생성, 설정 저장, 완료 처리를 검증합니다.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from jongji.main import app


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
        )
        resp = await client.post(
            "/api/v1/setup/admin",
            json={
                "email": "admin2@example.com",
                "password": "AdminPass123",
                "name": "Admin2",
            },
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
        )
        assert resp.status_code == 422


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
        )
        await client.post("/api/v1/setup/complete")
        # 완료 후 설정 변경 시도
        resp = await client.post(
            "/api/v1/setup/settings",
            json={"app_name": "Changed"},
        )
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
        )
        await client.post(
            "/api/v1/setup/settings",
            json={
                "app_name": "MyApp",
                "timezone": "Asia/Seoul",
            },
        )
        resp = await client.post("/api/v1/setup/complete")
        assert resp.status_code == 200

        # 상태 확인
        status_resp = await client.get("/api/v1/setup/status")
        assert status_resp.json()["setup_completed"] is True

    async def test_complete_without_admin(self, client):
        """관리자 없이 설정 완료 시 400 반환."""
        resp = await client.post("/api/v1/setup/complete")
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
        )
        await client.post("/api/v1/setup/complete")
        resp = await client.post("/api/v1/setup/complete")
        assert resp.status_code == 409
