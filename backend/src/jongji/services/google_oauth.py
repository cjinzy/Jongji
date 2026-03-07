"""Google OAuth 2.0 서비스 모듈.

Google OAuth 2.0 인증 흐름을 처리합니다:
- Authorization URL 생성
- 인증 코드를 액세스 토큰으로 교환
- Google 사용자 정보 조회
- OAuth 설정을 system_settings 테이블에 암호화하여 저장/조회/삭제
"""

import traceback
from urllib.parse import urlencode

import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.config import settings
from jongji.models.system import SystemSetting
from jongji.services.crypto import decrypt_value, encrypt_value, mask_secret

# ── Google OAuth 엔드포인트 ────────────────────────────────────────
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# ── system_settings 키 상수 ───────────────────────────────────────
_KEY_CLIENT_ID = "google_oauth_client_id"
_KEY_CLIENT_SECRET = "google_oauth_client_secret"  # 암호화 저장
_KEY_REDIRECT_URI = "google_oauth_redirect_uri"


async def get_oauth_config(db: AsyncSession) -> dict | None:
    """DB에서 Google OAuth 설정을 조회합니다.

    system_settings 테이블에서 설정을 먼저 조회하고,
    없는 경우 환경 변수(settings)로 fallback합니다.
    둘 다 없으면 None을 반환합니다.

    client_secret은 DB에 암호화되어 저장되므로 조회 시 복호화합니다.

    Args:
        db: 비동기 SQLAlchemy 세션.

    Returns:
        dict | None: {"client_id", "client_secret", "redirect_uri"} 또는 None.
    """
    try:
        client_id = await _get_setting(db, _KEY_CLIENT_ID)
        encrypted_secret = await _get_setting(db, _KEY_CLIENT_SECRET)
        redirect_uri = await _get_setting(db, _KEY_REDIRECT_URI)

        # DB에 없으면 환경 변수로 fallback
        if not client_id:
            client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET if not encrypted_secret else decrypt_value(encrypted_secret)
        if not redirect_uri:
            redirect_uri = settings.GOOGLE_REDIRECT_URI

        if not client_id or not client_secret:
            return None

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }
    except Exception:
        logger.error("Google OAuth 설정 조회 실패:\n{}", traceback.format_exc())
        return None


async def get_oauth_config_masked(db: AsyncSession) -> dict | None:
    """DB에서 Google OAuth 설정을 마스킹하여 조회합니다.

    client_secret은 마스킹 처리됩니다 (예: "****abcd").

    Args:
        db: 비동기 SQLAlchemy 세션.

    Returns:
        dict | None: {"client_id", "client_secret_masked", "redirect_uri", "is_configured"}
        또는 None (설정 없음).
    """
    config = await get_oauth_config(db)
    if config is None:
        return None

    return {
        "client_id": config["client_id"],
        "client_secret_masked": mask_secret(config["client_secret"]),
        "redirect_uri": config["redirect_uri"],
        "is_configured": True,
    }


async def save_oauth_config(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    db: AsyncSession,
) -> None:
    """Google OAuth 설정을 DB에 저장합니다.

    client_secret은 Fernet으로 암호화하여 저장합니다.
    기존 값이 있으면 업데이트하고, 없으면 새로 생성합니다 (upsert).

    Note:
        이 함수는 db.commit()을 호출하지 않습니다. 호출자가 트랜잭션을 관리합니다.

    Args:
        client_id: Google OAuth 클라이언트 ID.
        client_secret: Google OAuth 클라이언트 시크릿 (평문; 저장 시 암호화됨).
        redirect_uri: OAuth 콜백 URI.
        db: 비동기 SQLAlchemy 세션.
    """
    try:
        encrypted_secret = encrypt_value(client_secret)

        await _upsert_setting(db, _KEY_CLIENT_ID, client_id)
        await _upsert_setting(db, _KEY_CLIENT_SECRET, encrypted_secret)
        await _upsert_setting(db, _KEY_REDIRECT_URI, redirect_uri)

        logger.info(
            "Google OAuth 설정 저장 완료 — client_id={}, secret={}",
            client_id,
            mask_secret(client_secret),
        )
    except Exception:
        logger.error("Google OAuth 설정 저장 실패:\n{}", traceback.format_exc())
        raise


async def delete_oauth_config(db: AsyncSession) -> bool:
    """DB에서 Google OAuth 설정을 삭제합니다.

    Note:
        이 함수는 db.commit()을 호출하지 않습니다. 호출자가 트랜잭션을 관리합니다.

    Args:
        db: 비동기 SQLAlchemy 세션.

    Returns:
        bool: 삭제 성공 여부 (설정이 존재했으면 True).
    """
    keys = [_KEY_CLIENT_ID, _KEY_CLIENT_SECRET, _KEY_REDIRECT_URI]
    deleted_any = False

    for key in keys:
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        row = result.scalar_one_or_none()
        if row:
            await db.delete(row)
            deleted_any = True

    if deleted_any:
        logger.info("Google OAuth 설정 삭제 완료")
    return deleted_any


def build_authorize_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Google OAuth 인증 URL을 생성합니다.

    Args:
        client_id: Google OAuth 클라이언트 ID.
        redirect_uri: OAuth 콜백 URI.
        state: CSRF 방지를 위한 무작위 상태 문자열.

    Returns:
        str: 사용자를 리다이렉트할 Google 인증 URL.
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    """인증 코드를 Google 액세스 토큰으로 교환합니다.

    Args:
        code: Google 인증 콜백에서 받은 authorization code.
        client_id: Google OAuth 클라이언트 ID.
        client_secret: Google OAuth 클라이언트 시크릿.
        redirect_uri: OAuth 콜백 URI.

    Returns:
        dict: Google 토큰 응답 (access_token, id_token 등 포함).

    Raises:
        httpx.HTTPStatusError: Google 토큰 엔드포인트 오류 시.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError:
        logger.error("Google 토큰 교환 HTTP 오류:\n{}", traceback.format_exc())
        raise
    except Exception:
        logger.error("Google 토큰 교환 실패:\n{}", traceback.format_exc())
        raise


async def get_google_userinfo(access_token: str) -> dict:
    """Google 액세스 토큰으로 사용자 정보를 조회합니다.

    Args:
        access_token: Google OAuth 액세스 토큰.

    Returns:
        dict: Google 사용자 정보 (sub, email, name, picture 등).

    Raises:
        httpx.HTTPStatusError: Google userinfo 엔드포인트 오류 시.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            logger.debug("Google 사용자 정보 조회 완료 — email={}", data.get("email"))
            return data
    except httpx.HTTPStatusError:
        logger.error("Google 사용자 정보 조회 HTTP 오류:\n{}", traceback.format_exc())
        raise
    except Exception:
        logger.error("Google 사용자 정보 조회 실패:\n{}", traceback.format_exc())
        raise


# ── 내부 헬퍼 함수 ─────────────────────────────────────────────────


async def _get_setting(db: AsyncSession, key: str) -> str | None:
    """system_settings 테이블에서 키에 해당하는 값을 조회합니다.

    Args:
        db: 비동기 SQLAlchemy 세션.
        key: 조회할 설정 키.

    Returns:
        str | None: 설정 값, 없으면 None.
    """
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    row = result.scalar_one_or_none()
    return row.value if row else None


async def _upsert_setting(db: AsyncSession, key: str, value: str) -> None:
    """system_settings 테이블에 키-값을 upsert합니다.

    기존 행이 있으면 값을 업데이트하고, 없으면 새로 삽입합니다.

    Args:
        db: 비동기 SQLAlchemy 세션.
        key: 설정 키.
        value: 저장할 값.
    """
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(SystemSetting(key=key, value=value))
