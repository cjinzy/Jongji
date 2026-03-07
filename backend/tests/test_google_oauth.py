"""google_oauth 서비스 단위 테스트.

DB 설정 로드/저장/삭제, authorize URL 생성, httpx 모킹을 통한 토큰 교환 등을 검증합니다.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGetOAuthConfig:
    """get_oauth_config() 함수 테스트."""

    async def test_get_oauth_config_from_db(self, db_session):
        """DB에 저장된 OAuth 설정을 정상적으로 불러옴."""
        from jongji.services import google_oauth as svc

        await svc.save_oauth_config(
            client_id="test-client-id",
            client_secret="test-secret",
            redirect_uri="http://localhost/callback",
            db=db_session,
        )
        await db_session.flush()

        config = await svc.get_oauth_config(db_session)
        assert config is not None
        assert config["client_id"] == "test-client-id"
        assert config["redirect_uri"] == "http://localhost/callback"
        # client_secret은 복호화된 값이어야 함
        assert config["client_secret"] == "test-secret"

    async def test_get_oauth_config_none_when_not_set(self, db_session):
        """DB+env 모두 OAuth 미설정 시 None 반환."""
        from jongji.services import google_oauth as svc

        with patch("jongji.services.google_oauth.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = None
            mock_settings.GOOGLE_CLIENT_SECRET = None
            mock_settings.GOOGLE_REDIRECT_URI = None
            config = await svc.get_oauth_config(db_session)
            # DB에 설정이 없고 env도 None이면 None 반환
            # (DB 설정이 있으면 그걸 우선 반환하므로 이 테스트는 DB 미설정 상태여야 함)
            # conftest의 rollback 덕분에 DB는 빈 상태
            assert config is None


class TestSaveOAuthConfig:
    """save_oauth_config() 함수 테스트."""

    async def test_save_oauth_config_encrypted(self, db_session):
        """저장 후 DB의 client_secret 값이 암호화되어 있는지 확인."""
        from sqlalchemy import select

        from jongji.models.system import SystemSetting
        from jongji.services import google_oauth as svc

        await svc.save_oauth_config(
            client_id="encrypted-test-id",
            client_secret="plain-secret-value",
            redirect_uri="http://localhost/cb",
            db=db_session,
        )
        await db_session.flush()

        # DB에서 직접 조회하여 암호화 여부 확인
        result = await db_session.execute(
            select(SystemSetting).where(SystemSetting.key == "google_oauth_client_secret")
        )
        setting = result.scalar_one_or_none()
        assert setting is not None
        # 저장된 값은 평문이 아니어야 함
        assert setting.value != "plain-secret-value"
        # 복호화하면 원문과 일치해야 함
        from jongji.services.crypto import decrypt_value

        assert decrypt_value(setting.value) == "plain-secret-value"


class TestBuildAuthorizeUrl:
    """build_authorize_url() 함수 테스트."""

    def test_build_authorize_url_contains_required_params(self):
        """URL에 client_id, redirect_uri, state가 포함되어야 함."""
        from jongji.services import google_oauth as svc

        url = svc.build_authorize_url(
            client_id="my-client-id",
            redirect_uri="http://localhost/callback",
            state="random-state-value",
        )
        assert "my-client-id" in url
        assert "localhost" in url
        assert "random-state-value" in url
        assert "accounts.google.com" in url or "oauth2" in url

    def test_build_authorize_url_includes_email_scope(self):
        """URL에 email 스코프가 포함되어야 함."""
        from jongji.services import google_oauth as svc

        url = svc.build_authorize_url(
            client_id="cid",
            redirect_uri="http://localhost/cb",
            state="st",
        )
        assert "email" in url


class TestExchangeCodeForTokens:
    """exchange_code_for_tokens() — httpx 모킹 테스트."""

    async def test_exchange_code_for_tokens_success(self):
        """Google 토큰 교환 성공 시 access_token 포함 dict 반환."""
        from unittest.mock import patch

        from jongji.services import google_oauth as svc

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "ya29.test-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await svc.exchange_code_for_tokens(
                code="auth-code-123",
                client_id="client-id",
                client_secret="client-secret",
                redirect_uri="http://localhost/callback",
            )
        assert result["access_token"] == "ya29.test-token"


class TestDeleteOAuthConfig:
    """delete_oauth_config() 함수 테스트."""

    async def test_delete_oauth_config_returns_true(self, db_session):
        """설정 삭제 후 True 반환, 재조회 시 None."""
        from jongji.services import google_oauth as svc

        await svc.save_oauth_config(
            client_id="to-delete-id",
            client_secret="to-delete-secret",
            redirect_uri="http://localhost/del",
            db=db_session,
        )
        await db_session.flush()

        deleted = await svc.delete_oauth_config(db_session)
        assert deleted is True

        await db_session.flush()
        config = await svc.get_oauth_config(db_session)
        assert config is None

    async def test_delete_oauth_config_returns_false_when_not_set(self, db_session):
        """설정이 없을 때 삭제 시 False 반환."""
        from jongji.services import google_oauth as svc

        with patch("jongji.services.google_oauth.settings") as mock_settings:
            mock_settings.GOOGLE_CLIENT_ID = None
            result = await svc.delete_oauth_config(db_session)
            assert result is False
