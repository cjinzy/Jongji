"""AUTH_DISABLED 기능 테스트.

AUTH_DISABLED=true일 때 인증 우회 동작을 검증합니다.
"""

from unittest.mock import patch

import bcrypt as _bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from jongji.main import app
from jongji.models.user import User


def _hash_password(password: str) -> str:
    """테스트용 비밀번호 해싱."""
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


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
async def admin_user(db_session) -> User:
    """테스트용 관리자 사용자 생성.

    Args:
        db_session: 테스트용 DB 세션 픽스처.

    Returns:
        User: 관리자 사용자 모델.
    """
    user = User(
        email="admin@test.com",
        name="Test Admin",
        password_hash=_hash_password("TestPass1!"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


class TestDevStatus:
    """GET /auth/dev-status 엔드포인트 테스트."""

    async def test_dev_status_disabled_by_default(self, client):
        """기본값으로 AUTH_DISABLED=false를 반환합니다."""
        res = await client.get("/api/v1/auth/dev-status")
        assert res.status_code == 200
        assert res.json() == {"auth_disabled": False}

    @patch("jongji.api.auth.settings")
    async def test_dev_status_enabled(self, mock_settings, client):
        """AUTH_DISABLED=true일 때 활성 상태를 반환합니다."""
        mock_settings.AUTH_DISABLED = True
        res = await client.get("/api/v1/auth/dev-status")
        assert res.status_code == 200
        assert res.json() == {"auth_disabled": True}


class TestAuthDisabledBypass:
    """AUTH_DISABLED=true일 때 인증 우회 동작 테스트."""

    @patch("jongji.api.deps.settings")
    async def test_protected_route_accessible_without_token(
        self, mock_settings, client, admin_user,
    ):
        """AUTH_DISABLED 시 토큰 없이 보호된 엔드포인트에 접근 가능합니다."""
        mock_settings.AUTH_DISABLED = True
        mock_settings.SECRET_KEY = "test-key"
        res = await client.get("/api/v1/users/me")
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "admin@test.com"

    async def test_protected_route_requires_token_when_enabled(self, client, admin_user):
        """AUTH_DISABLED=false(기본)일 때 토큰 없이 401을 반환합니다."""
        res = await client.get("/api/v1/users/me")
        assert res.status_code == 401

    @patch("jongji.api.deps.settings")
    async def test_returns_admin_user(self, mock_settings, client, admin_user):
        """AUTH_DISABLED 시 관리자 사용자를 반환합니다."""
        mock_settings.AUTH_DISABLED = True
        mock_settings.SECRET_KEY = "test-key"
        res = await client.get("/api/v1/users/me")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Test Admin"
        assert data["email"] == "admin@test.com"

    @patch("jongji.api.deps.settings")
    async def test_no_admin_user_falls_through(self, mock_settings, client):
        """AUTH_DISABLED이지만 관리자가 없으면 일반 인증 흐름으로 진행합니다."""
        mock_settings.AUTH_DISABLED = True
        mock_settings.SECRET_KEY = "test-key"
        res = await client.get("/api/v1/users/me")
        assert res.status_code == 401
