"""인증 API 라우터.

회원가입, 로그인, 토큰 갱신, 로그아웃, Google OAuth 엔드포인트를 제공합니다.
"""

import hmac
import secrets
import traceback
from datetime import UTC

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.api.deps import get_current_user
from jongji.config import settings
from jongji.database import get_db
from jongji.models.user import User
from jongji.schemas.user import TokenResponse, UserCreate, UserLogin
from jongji.services import google_oauth as google_oauth_service
from jongji.services.auth_service import (
    create_access_token,
    create_refresh_token,
    get_or_create_google_user,
    login,
    register,
    verify_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """새 사용자를 등록하고 액세스 토큰을 발급합니다.

    Args:
        data: 회원가입 요청 데이터.
        db: 비동기 DB 세션.

    Returns:
        TokenResponse: 액세스 토큰.
    """
    try:
        user = await register(data, db)
        await db.commit()
    except ValueError as e:
        logger.warning(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception:
        logger.error(f"Unexpected registration error: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    access_token = create_access_token(user.id)
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    data: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """이메일/비밀번호로 로그인합니다.

    액세스 토큰을 JSON으로 반환하고, 리프레시 토큰은 HttpOnly 쿠키로 설정합니다.

    Args:
        data: 로그인 요청 데이터.
        request: HTTP 요청 객체.
        response: HTTP 응답 객체.
        db: 비동기 DB 세션.

    Returns:
        TokenResponse: 액세스 토큰.
    """
    try:
        user = await login(data, db)
    except PermissionError as e:
        logger.warning(f"Account locked: {e}")
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=str(e),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    except Exception:
        logger.error(f"Unexpected login error: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    access_token = create_access_token(user.id)
    device_info = request.headers.get("User-Agent")
    raw_refresh = await create_refresh_token(user.id, device_info, db)

    # Refresh token - HttpOnly 쿠키
    is_secure = not settings.CORS_ORIGINS or "localhost" not in settings.CORS_ORIGINS[0]
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/api/v1/auth/refresh",
    )

    # CSRF double-submit 쿠키
    csrf_value = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_value,
        httponly=False,
        secure=is_secure,
        samesite="lax",
    )

    await db.commit()
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    csrf_token: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """리프레시 토큰으로 새 액세스 토큰을 발급합니다.

    HttpOnly 쿠키의 refresh_token과 CSRF Double Submit Cookie를 검증합니다.

    Args:
        response: HTTP 응답 객체.
        refresh_token: 리프레시 토큰 (쿠키).
        csrf_token: CSRF 토큰 (쿠키에서 자동 전송).
        x_csrf_token: CSRF 토큰 (요청 헤더).
        db: 비동기 DB 세션.

    Returns:
        TokenResponse: 새 액세스 토큰.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    # CSRF Double Submit Cookie 검증: 쿠키 값과 헤더 값이 일치해야 함
    if not x_csrf_token or not csrf_token or not hmac.compare_digest(csrf_token, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token mismatch",
        )

    token_record = await verify_refresh_token(refresh_token, db)
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token = create_access_token(token_record.user_id)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """로그아웃합니다 (리프레시 토큰 무효화).

    Args:
        response: HTTP 응답 객체.
        refresh_token: 리프레시 토큰 (쿠키).
        user: 현재 인증된 사용자.
        db: 비동기 DB 세션.

    Returns:
        dict: 로그아웃 성공 메시지.
    """
    if refresh_token:
        token_record = await verify_refresh_token(refresh_token, db)
        if token_record:
            from datetime import datetime

            token_record.revoked_at = datetime.now(UTC)
            await db.flush()
            await db.commit()

    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh")
    response.delete_cookie("csrf_token")
    return {"detail": "Logged out"}


def _get_frontend_origin() -> str:
    """프론트엔드 origin을 반환합니다.

    Returns:
        str: CORS_ORIGINS 첫 번째 항목 또는 기본값 'http://localhost:5173'.
    """
    if settings.CORS_ORIGINS:
        return settings.CORS_ORIGINS[0]
    return "http://localhost:5173"


@router.get("/google/authorize")
async def google_authorize(
    db: AsyncSession = Depends(get_db),
):
    """Google OAuth 인증 URL로 리다이렉트합니다.

    DB에서 OAuth 설정을 로드하고 state를 생성하여 쿠키에 저장한 후,
    Google 인증 페이지로 리다이렉트합니다.

    Args:
        db: 비동기 DB 세션.

    Returns:
        RedirectResponse: Google 인증 URL로의 리다이렉트.

    Raises:
        HTTPException: Google OAuth 설정이 없는 경우 404.
    """
    config = await google_oauth_service.get_oauth_config(db)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    authorize_url = google_oauth_service.build_authorize_url(
        client_id=config["client_id"],
        redirect_uri=config["redirect_uri"],
        state=state,
    )

    is_secure = not settings.CORS_ORIGINS or "localhost" not in settings.CORS_ORIGINS[0]
    redirect = RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=300,
    )
    return redirect


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str,
    state: str,
    oauth_state: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Google OAuth 콜백을 처리합니다.

    state 쿠키를 검증하고, 코드를 토큰으로 교환하고, 사용자 정보를 가져와서
    사용자를 생성하거나 기존 계정에 연결한 후 프론트엔드로 리다이렉트합니다.

    Args:
        request: HTTP 요청 객체.
        code: Google에서 받은 인증 코드.
        state: CSRF 방지용 state 파라미터.
        oauth_state: 쿠키에 저장된 state 값.
        db: 비동기 DB 세션.

    Returns:
        RedirectResponse: 액세스 토큰을 포함한 프론트엔드 /auth/callback 으로 리다이렉트.
    """
    origin = _get_frontend_origin()
    is_secure = "localhost" not in origin

    # state 검증
    if not oauth_state or not hmac.compare_digest(state, oauth_state):
        logger.warning(f"OAuth state mismatch: expected={oauth_state!r}, got={state!r}")
        redirect = RedirectResponse(
            url=f"{origin}/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )
        redirect.delete_cookie("oauth_state")
        return redirect

    try:
        config = await google_oauth_service.get_oauth_config(db)
        if config is None:
            raise ValueError("Google OAuth is not configured")

        # 코드 → 토큰 교환
        tokens = await google_oauth_service.exchange_code_for_tokens(
            code=code,
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            redirect_uri=config["redirect_uri"],
        )

        # Google 사용자 정보 조회
        userinfo = await google_oauth_service.get_google_userinfo(tokens["access_token"])

        # 사용자 생성 또는 연결
        user = await get_or_create_google_user(userinfo, db)

        # 토큰 발급
        access_token = create_access_token(user.id)
        device_info = request.headers.get("User-Agent")
        raw_refresh = await create_refresh_token(user.id, device_info, db)
        await db.commit()

        # 프론트엔드로 리다이렉트
        redirect = RedirectResponse(
            url=f"{origin}/auth/callback?token={access_token}",
            status_code=status.HTTP_302_FOUND,
        )

        # Refresh token - HttpOnly 쿠키
        redirect.set_cookie(
            key="refresh_token",
            value=raw_refresh,
            httponly=True,
            secure=is_secure,
            samesite="lax",
            max_age=7 * 24 * 60 * 60,
            path="/api/v1/auth/refresh",
        )

        # CSRF double-submit 쿠키
        csrf_value = secrets.token_urlsafe(32)
        redirect.set_cookie(
            key="csrf_token",
            value=csrf_value,
            httponly=False,
            secure=is_secure,
            samesite="lax",
        )

        # state 쿠키 삭제
        redirect.delete_cookie("oauth_state")
        return redirect

    except Exception:
        logger.error(f"Google OAuth callback failed: {traceback.format_exc()}")
        redirect = RedirectResponse(
            url=f"{origin}/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND,
        )
        redirect.delete_cookie("oauth_state")
        return redirect
