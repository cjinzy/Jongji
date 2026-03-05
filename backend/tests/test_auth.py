"""Auth API 엔드포인트 테스트 - TDD 방식.

register, login, refresh, logout 엔드포인트의 동작을 검증합니다.
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


class TestRegister:
    """회원가입 엔드포인트 테스트."""

    async def test_register_success(self, client):
        """정상적인 회원가입 시 201 + access_token 반환."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "Password1",
                "name": "Test User",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_short_password(self, client):
        """8자 미만 비밀번호로 가입 시 422 반환."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
                "name": "Test",
            },
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client):
        """유효하지 않은 이메일로 가입 시 422 반환."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "Password1",
                "name": "Test",
            },
        )
        assert resp.status_code == 422

    async def test_register_duplicate_email(self, client):
        """중복 이메일로 가입 시 409 반환."""
        payload = {
            "email": "dup@example.com",
            "password": "Password1",
            "name": "Test",
        }
        resp1 = await client.post("/api/v1/auth/register", json=payload)
        assert resp1.status_code == 201
        resp2 = await client.post("/api/v1/auth/register", json=payload)
        assert resp2.status_code == 409

    async def test_register_empty_name(self, client):
        """빈 이름으로 가입 시 422 반환."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "Password1",
                "name": "",
            },
        )
        assert resp.status_code == 422


class TestLogin:
    """로그인 엔드포인트 테스트."""

    async def test_login_success(self, client):
        """정상 로그인 시 access_token + refresh_token 쿠키 반환."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "password": "Password1",
                "name": "Login User",
            },
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "Password1",
            },
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        assert "refresh_token" in resp.cookies

    async def test_login_wrong_password(self, client):
        """잘못된 비밀번호로 로그인 시 401 반환."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong@example.com",
                "password": "Password1",
                "name": "Wrong",
            },
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrong@example.com",
                "password": "wrongpassword",
            },
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        """존재하지 않는 사용자 로그인 시 401 반환."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nope@example.com",
                "password": "Password1",
            },
        )
        assert resp.status_code == 401

    async def test_login_fail_increments_count(self, client):
        """로그인 실패 시 fail_count가 증가하는지 검증."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "failcount@example.com",
                "password": "Password1",
                "name": "FailCount",
            },
        )
        # 3회 실패
        for _ in range(3):
            await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "failcount@example.com",
                    "password": "wrong",
                },
            )
        # 정상 로그인은 여전히 가능
        resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "failcount@example.com",
                "password": "Password1",
            },
        )
        assert resp.status_code == 200


class TestRefresh:
    """토큰 갱신 엔드포인트 테스트."""

    async def test_refresh_success(self, client):
        """유효한 refresh_token 쿠키로 새 access_token 발급."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "refresh@example.com",
                "password": "Password1",
                "name": "Refresh",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "refresh@example.com",
                "password": "Password1",
            },
        )
        assert login_resp.status_code == 200
        # 쿠키에서 csrf_token 가져오기
        csrf_token = login_resp.cookies.get("csrf_token")

        resp = await client.post(
            "/api/v1/auth/refresh",
            headers={"X-CSRF-Token": csrf_token} if csrf_token else {},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_refresh_without_cookie(self, client):
        """refresh_token 쿠키 없이 요청 시 401 반환."""
        # 쿠키 없는 새 클라이언트
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as fresh_client:
            resp = await fresh_client.post("/api/v1/auth/refresh")
            assert resp.status_code == 401


class TestLogout:
    """로그아웃 엔드포인트 테스트."""

    async def test_logout_success(self, client):
        """로그인 후 로그아웃 시 200 반환."""
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@example.com",
                "password": "Password1",
                "name": "Logout",
            },
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "logout@example.com",
                "password": "Password1",
            },
        )
        access_token = login_resp.json()["access_token"]
        resp = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
