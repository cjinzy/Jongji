"""Auth 서비스 단위 테스트.

비밀번호 해싱, JWT 토큰 생성/검증, Google OAuth 계정 연결 등 핵심 인증 로직을 검증합니다.
"""

import uuid

from jongji.services.auth_service import (
    _hash_password_sync,
    _verify_password_sync,
    create_access_token,
    get_or_create_google_user,
    hash_password,
    verify_access_token,
)


class TestPasswordHashing:
    """비밀번호 해싱/검증 테스트."""

    def test_hash_password_returns_hash(self):
        """비밀번호 해싱 결과가 원본과 다른지 확인."""
        hashed = _hash_password_sync("password123")
        assert hashed != "password123"
        assert hashed.startswith("$2")  # bcrypt prefix

    def test_verify_password_correct(self):
        """올바른 비밀번호 검증 성공."""
        hashed = _hash_password_sync("password123")
        assert _verify_password_sync("password123", hashed) is True

    def test_verify_password_incorrect(self):
        """잘못된 비밀번호 검증 실패."""
        hashed = _hash_password_sync("password123")
        assert _verify_password_sync("wrongpassword", hashed) is False


class TestJWT:
    """JWT 토큰 생성/검증 테스트."""

    def test_create_and_verify_token(self):
        """토큰 생성 후 검증 시 동일한 user_id 반환."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        decoded_id = verify_access_token(token)
        assert decoded_id == user_id

    def test_verify_invalid_token(self):
        """유효하지 않은 토큰 검증 시 None 반환."""
        result = verify_access_token("invalid.token.here")
        assert result is None

    def test_token_is_string(self):
        """토큰이 문자열 형태인지 확인."""
        token = create_access_token(uuid.uuid4())
        assert isinstance(token, str)
        assert len(token) > 0


class TestGetOrCreateGoogleUser:
    """get_or_create_google_user() 이메일 충돌 자동 연결 테스트."""

    async def test_create_new_google_user(self, db_session):
        """Google 정보로 신규 사용자 생성."""
        google_data = {
            "sub": "google-id-new-001",
            "email": "newgoogleuser@example.com",
            "name": "New Google User",
            "picture": "https://example.com/pic.jpg",
        }
        user = await get_or_create_google_user(google_data, db_session)
        assert user.email == "newgoogleuser@example.com"
        assert user.google_id == "google-id-new-001"
        assert user.avatar_url == "https://example.com/pic.jpg"

    async def test_returns_existing_google_user(self, db_session):
        """같은 google_id로 재요청 시 기존 사용자 반환."""
        google_data = {
            "sub": "google-id-existing-002",
            "email": "existing@example.com",
            "name": "Existing",
            "picture": None,
        }
        user1 = await get_or_create_google_user(google_data, db_session)
        await db_session.flush()
        user2 = await get_or_create_google_user(google_data, db_session)
        assert user1.id == user2.id

    async def test_email_conflict_links_google_id(self, db_session):
        """이메일 충돌 시 기존 계정에 google_id 자동 연결 (password_hash 있어도)."""
        from jongji.models.user import User

        # 비밀번호 계정 생성
        existing = User(
            email="conflict@example.com",
            name="Conflict User",
            password_hash=await hash_password("Password1"),
        )
        db_session.add(existing)
        await db_session.flush()

        google_data = {
            "sub": "google-id-conflict-003",
            "email": "conflict@example.com",
            "name": "Conflict",
            "picture": "https://example.com/new-pic.jpg",
        }
        linked_user = await get_or_create_google_user(google_data, db_session)
        assert linked_user.id == existing.id
        assert linked_user.google_id == "google-id-conflict-003"
        # avatar_url이 없었으므로 Google picture로 업데이트
        assert linked_user.avatar_url == "https://example.com/new-pic.jpg"

    async def test_email_conflict_no_value_error(self, db_session):
        """이메일 충돌 시 ValueError가 발생하지 않음."""
        from jongji.models.user import User

        existing = User(
            email="noerror@example.com",
            name="No Error",
            password_hash=await hash_password("Password1"),
        )
        db_session.add(existing)
        await db_session.flush()

        google_data = {
            "sub": "google-id-noerror-004",
            "email": "noerror@example.com",
            "name": "No Error Google",
            "picture": None,
        }
        # ValueError가 발생하지 않아야 함
        user = await get_or_create_google_user(google_data, db_session)
        assert user is not None

    async def test_avatar_not_overwritten_if_exists(self, db_session):
        """기존 avatar_url이 있으면 Google picture로 덮어쓰지 않음."""
        from jongji.models.user import User

        existing = User(
            email="avatar@example.com",
            name="Avatar User",
            password_hash=await hash_password("Password1"),
            avatar_url="https://existing-avatar.com/pic.jpg",
        )
        db_session.add(existing)
        await db_session.flush()

        google_data = {
            "sub": "google-id-avatar-005",
            "email": "avatar@example.com",
            "name": "Avatar",
            "picture": "https://google-new-pic.com/pic.jpg",
        }
        user = await get_or_create_google_user(google_data, db_session)
        # 기존 avatar_url 유지
        assert user.avatar_url == "https://existing-avatar.com/pic.jpg"
