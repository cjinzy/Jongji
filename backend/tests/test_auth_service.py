"""Auth 서비스 단위 테스트.

비밀번호 해싱, JWT 토큰 생성/검증 등 핵심 인증 로직을 검증합니다.
"""

import uuid

from jongji.services.auth_service import (
    _hash_password_sync,
    _verify_password_sync,
    create_access_token,
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
