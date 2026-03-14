"""인증 서비스 모듈.

비밀번호 해싱, JWT 토큰 생성/검증, 회원가입/로그인 로직을 담당합니다.
"""

import asyncio
import hashlib
import secrets
import traceback
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.config import settings
from jongji.models.user import RefreshToken, User
from jongji.schemas.user import UserCreate, UserLogin  # noqa: F401

ALGORITHM = "HS256"


def _hash_password_sync(password: str) -> str:
    """비밀번호를 bcrypt로 해싱합니다 (동기).

    Args:
        password: 평문 비밀번호.

    Returns:
        해싱된 비밀번호 문자열.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _verify_password_sync(plain: str, hashed: str) -> bool:
    """평문 비밀번호와 해시를 비교합니다 (동기).

    Args:
        plain: 평문 비밀번호.
        hashed: 해싱된 비밀번호.

    Returns:
        일치 여부.
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


async def hash_password(password: str) -> str:
    """비밀번호를 bcrypt로 해싱합니다 (비동기, event loop 블로킹 방지).

    Args:
        password: 평문 비밀번호.

    Returns:
        해싱된 비밀번호 문자열.
    """
    return await asyncio.to_thread(_hash_password_sync, password)


async def verify_password(plain: str, hashed: str) -> bool:
    """평문 비밀번호와 해시를 비교합니다 (비동기, event loop 블로킹 방지).

    Args:
        plain: 평문 비밀번호.
        hashed: 해싱된 비밀번호.

    Returns:
        일치 여부.
    """
    return await asyncio.to_thread(_verify_password_sync, plain, hashed)


def create_access_token(user_id: uuid.UUID) -> str:
    """JWT 액세스 토큰을 생성합니다.

    Args:
        user_id: 사용자 UUID.

    Returns:
        JWT 토큰 문자열.
    """
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> uuid.UUID | None:
    """JWT 액세스 토큰을 검증하고 user_id를 반환합니다.

    Args:
        token: JWT 토큰 문자열.

    Returns:
        사용자 UUID 또는 None (유효하지 않은 경우).
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            return None
        return uuid.UUID(sub)
    except (JWTError, ValueError):
        logger.debug(f"Invalid access token: {traceback.format_exc()}")
        return None


async def create_refresh_token(
    user_id: uuid.UUID,
    device_info: str | None,
    db: AsyncSession,
) -> str:
    """리프레시 토큰을 생성하고 DB에 해시를 저장합니다.

    Args:
        user_id: 사용자 UUID.
        device_info: 디바이스 정보 문자열.
        db: 비동기 DB 세션.

    Returns:
        생성된 리프레시 토큰 (raw).
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=device_info,
    )
    db.add(refresh_token)
    await db.flush()
    return raw_token


async def verify_refresh_token(token: str, db: AsyncSession) -> RefreshToken | None:
    """리프레시 토큰을 검증합니다.

    Args:
        token: 리프레시 토큰 (raw).
        db: 비동기 DB 세션.

    Returns:
        유효한 RefreshToken 객체 또는 None.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    return result.scalar_one_or_none()


async def register(data: UserCreate, db: AsyncSession) -> User:
    """새 사용자를 등록합니다.

    Args:
        data: 회원가입 요청 데이터.
        db: 비동기 DB 세션.

    Returns:
        생성된 User 객체.

    Raises:
        ValueError: 이메일이 이미 사용 중인 경우.
    """
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ValueError("Email already registered")

    user = User(
        email=data.email,
        name=data.name,
        password_hash=await hash_password(data.password),
    )
    db.add(user)
    await db.flush()
    return user


async def login(data: UserLogin, db: AsyncSession) -> User:
    """이메일/비밀번호로 로그인합니다.

    Args:
        data: 로그인 요청 데이터.
        db: 비동기 DB 세션.

    Returns:
        인증된 User 객체.

    Raises:
        ValueError: 인증 실패 시.
        PermissionError: 계정 잠금 시.
    """
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise ValueError("Invalid credentials")

    # 계정 잠금 확인
    check_login_security(user)

    if not await verify_password(data.password, user.password_hash):
        await handle_login_failure(user, db)
        raise ValueError("Invalid credentials")

    await handle_login_success(user, db)
    return user


def check_login_security(user: User) -> None:
    """로그인 보안 검사 (잠금 여부 확인).

    Args:
        user: 사용자 객체.

    Raises:
        PermissionError: 계정이 잠긴 경우.
    """
    if user.locked_until and user.locked_until > datetime.now(UTC):
        remaining = (user.locked_until - datetime.now(UTC)).seconds
        raise PermissionError(f"Account locked. Try again in {remaining} seconds.")


async def handle_login_failure(user: User, db: AsyncSession) -> None:
    """로그인 실패를 처리합니다 (실패 카운트 증가, 잠금 설정).

    10회 실패 시 15분 잠금을 설정합니다.

    Args:
        user: 사용자 객체.
        db: 비동기 DB 세션.
    """
    user.login_fail_count += 1
    if user.login_fail_count >= 10:
        user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
        logger.warning(f"Account locked for user {user.email} after {user.login_fail_count} failures")
    await db.flush()


async def handle_login_success(user: User, db: AsyncSession) -> None:
    """로그인 성공 시 실패 카운트를 초기화합니다.

    Args:
        user: 사용자 객체.
        db: 비동기 DB 세션.
    """
    user.login_fail_count = 0
    user.locked_until = None
    await db.flush()


async def get_or_create_google_user(google_data: dict, db: AsyncSession) -> User:
    """Google OAuth 데이터로 사용자를 조회하거나 생성합니다.

    Args:
        google_data: Google OAuth 응답 데이터.
        db: 비동기 DB 세션.

    Returns:
        사용자 객체. 이메일 충돌 시 Google ID를 자동으로 연결합니다.
    """
    google_id = google_data["sub"]
    email = google_data["email"]

    # google_id로 기존 사용자 조회
    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()
    if user:
        return user

    # 이메일로 기존 사용자 조회 (충돌 체크)
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        # 이메일 충돌 시 Google ID 자동 연결 (비밀번호 계정도 포함)
        existing.google_id = google_id
        if not existing.avatar_url and google_data.get("picture"):
            existing.avatar_url = google_data.get("picture")
        await db.flush()
        return existing

    # 새 사용자 생성
    user = User(
        email=email,
        name=google_data.get("name", email.split("@")[0]),
        google_id=google_id,
        avatar_url=google_data.get("picture"),
    )
    db.add(user)
    await db.flush()
    return user


async def check_setup_completed(db: AsyncSession) -> bool:
    """초기 설정 완료 여부를 확인합니다.

    Args:
        db: 비동기 DB 세션.

    Returns:
        설정 완료 여부.
    """
    from jongji.models.system import SystemSetting

    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == "setup_completed")
    )
    setting = result.scalar_one_or_none()
    return setting is not None and setting.value == "true"


async def get_user_count(db: AsyncSession) -> int:
    """등록된 사용자 수를 반환합니다.

    Args:
        db: 비동기 DB 세션.

    Returns:
        사용자 수.
    """
    result = await db.execute(select(func.count(User.id)))
    return result.scalar_one()
