"""User CRUD API 테스트 - TDD 방식.

사용자 프로필, 세션, API Key, 관리자 기능을 검증합니다.
ORM으로 직접 사용자를 생성하고 JWT를 발급하여 auth 의존성을 우회합니다.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from jongji.config import settings
from jongji.database import get_db
from jongji.main import app
from jongji.models.user import RefreshToken, User


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
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
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
async def normal_user(db_session) -> User:
    """일반 사용자를 ORM으로 직접 생성합니다."""
    user = User(
        email="user@example.com",
        name="Test User",
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
        email="admin@example.com",
        name="Admin User",
        password_hash=_hash_password("adminpass123"),
        is_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(normal_user: User) -> dict[str, str]:
    """일반 사용자 인증 헤더를 반환합니다."""
    token = _make_token(str(normal_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    """관리자 인증 헤더를 반환합니다."""
    token = _make_token(str(admin_user.id))
    return {"Authorization": f"Bearer {token}"}


class TestGetMe:
    """GET /api/v1/users/me 테스트."""

    async def test_get_me_success(self, client, auth_headers, normal_user):
        """인증된 사용자가 자신의 프로필을 조회할 수 있습니다."""
        resp = await client.get("/api/v1/users/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "user@example.com"
        assert data["name"] == "Test User"

    async def test_get_me_unauthenticated(self, client):
        """인증 없이 접근하면 401이 반환됩니다."""
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401


class TestUpdateMe:
    """PUT /api/v1/users/me 테스트."""

    async def test_update_name(self, client, auth_headers, normal_user):
        """사용자 이름을 변경할 수 있습니다."""
        resp = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    async def test_update_locale(self, client, auth_headers, normal_user):
        """locale을 ko 또는 en으로 변경할 수 있습니다."""
        resp = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"locale": "en"},
        )
        assert resp.status_code == 200
        assert resp.json()["locale"] == "en"

    async def test_update_invalid_locale(self, client, auth_headers, normal_user):
        """유효하지 않은 locale 값은 422를 반환합니다."""
        resp = await client.put(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"locale": "fr"},
        )
        assert resp.status_code == 422


class TestDeactivateMe:
    """DELETE /api/v1/users/me 테스트."""

    async def test_deactivate_success(self, client, auth_headers, normal_user):
        """일반 사용자는 자신의 계정을 비활성화할 수 있습니다."""
        resp = await client.delete("/api/v1/users/me", headers=auth_headers)
        assert resp.status_code == 204

    async def test_last_admin_cannot_deactivate(self, client, admin_headers, admin_user):
        """마지막 관리자는 계정을 비활성화할 수 없습니다 (409)."""
        resp = await client.delete("/api/v1/users/me", headers=admin_headers)
        assert resp.status_code == 409


class TestApiKeys:
    """API Key 관리 테스트."""

    async def test_create_api_key(self, client, auth_headers, normal_user):
        """API 키를 생성하면 jk_ 접두사의 raw_key가 반환됩니다."""
        resp = await client.post(
            "/api/v1/users/me/api-keys",
            headers=auth_headers,
            json={"name": "My Key"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "raw_key" in data
        assert data["raw_key"].startswith("jk_")
        assert data["name"] == "My Key"

    async def test_list_api_keys(self, client, auth_headers, normal_user):
        """생성된 API 키가 목록에 포함됩니다."""
        await client.post(
            "/api/v1/users/me/api-keys",
            headers=auth_headers,
            json={"name": "Key1"},
        )
        resp = await client.get("/api/v1/users/me/api-keys", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_delete_api_key(self, client, auth_headers, normal_user):
        """API 키를 삭제(비활성화)할 수 있습니다."""
        create_resp = await client.post(
            "/api/v1/users/me/api-keys",
            headers=auth_headers,
            json={"name": "ToDelete"},
        )
        key_id = create_resp.json()["id"]
        resp = await client.delete(
            f"/api/v1/users/me/api-keys/{key_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

        # 삭제 후 목록에서 사라져야 함
        list_resp = await client.get("/api/v1/users/me/api-keys", headers=auth_headers)
        key_ids = [k["id"] for k in list_resp.json()]
        assert key_id not in key_ids


class TestSessions:
    """세션 관리 테스트."""

    async def test_list_sessions(self, client, auth_headers, normal_user):
        """활성 세션 목록을 조회할 수 있습니다."""
        resp = await client.get("/api/v1/users/me/sessions", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_list_sessions_with_token(self, client, auth_headers, normal_user, db_session):
        """리프레시 토큰이 있으면 세션 목록에 포함됩니다."""
        token = RefreshToken(
            user_id=normal_user.id,
            token_hash="fakehash",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            device_info="Test Device",
        )
        db_session.add(token)
        await db_session.flush()

        resp = await client.get("/api/v1/users/me/sessions", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_revoke_session(self, client, auth_headers, normal_user, db_session):
        """특정 세션을 폐기할 수 있습니다."""
        token = RefreshToken(
            user_id=normal_user.id,
            token_hash="fakehash2",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            device_info="To Revoke",
        )
        db_session.add(token)
        await db_session.flush()
        await db_session.refresh(token)

        resp = await client.delete(
            f"/api/v1/users/me/sessions/{token.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204


class TestAdmin:
    """관리자 API 테스트."""

    async def test_get_settings(self, client, admin_headers, admin_user):
        """관리자가 시스템 설정을 조회할 수 있습니다."""
        resp = await client.get("/api/v1/admin/settings", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    async def test_update_settings(self, client, admin_headers, admin_user):
        """관리자가 시스템 설정을 업데이트할 수 있습니다."""
        resp = await client.put(
            "/api/v1/admin/settings",
            headers=admin_headers,
            json={"maintenance_mode": "false"},
        )
        assert resp.status_code == 200
        assert resp.json()["maintenance_mode"] == "false"

    async def test_non_admin_forbidden(self, client, auth_headers, normal_user):
        """일반 사용자는 관리자 API에 접근할 수 없습니다 (403)."""
        resp = await client.get("/api/v1/admin/settings", headers=auth_headers)
        assert resp.status_code == 403

    async def test_last_admin_cannot_be_removed(self, client, admin_headers, admin_user):
        """마지막 관리자의 관리자 역할을 해제할 수 없습니다 (409)."""
        resp = await client.put(
            f"/api/v1/admin/users/{admin_user.id}/role",
            headers=admin_headers,
            json={"is_admin": False},
        )
        assert resp.status_code == 409

    async def test_set_user_as_admin(self, client, admin_headers, admin_user, normal_user):
        """일반 사용자를 관리자로 승격할 수 있습니다."""
        resp = await client.put(
            f"/api/v1/admin/users/{normal_user.id}/role",
            headers=admin_headers,
            json={"is_admin": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is True
