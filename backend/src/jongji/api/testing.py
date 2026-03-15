"""E2E 테스트 전용 API 라우터.

E2E_TESTING=true 환경변수가 설정된 경우에만 main.py에서 등록됩니다.
프로덕션 환경에서는 절대 활성화하지 마세요.
"""

import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.database import get_db
from jongji.models.system import SystemSetting
from jongji.models.user import User
from jongji.schemas.user import SetupInitRequest
from jongji.services.auth_service import hash_password

router = APIRouter(prefix="/test", tags=["testing"])
setup_router = APIRouter(prefix="/setup", tags=["testing"])


@router.post("/reset-db")
async def reset_database(db: AsyncSession = Depends(get_db)):
    """모든 테이블 데이터를 삭제합니다 (alembic_version 제외).

    E2E 테스트 간 DB 상태를 초기화하기 위한 엔드포인트입니다.
    TRUNCATE CASCADE로 모든 테이블을 비웁니다.

    Args:
        db: 비동기 DB 세션.

    Returns:
        dict: 리셋 성공 메시지.
    """
    try:
        # 모든 사용자 테이블 이름 조회 (alembic_version 제외)
        result = await db.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' "
                "AND tablename != 'alembic_version'"
            )
        )
        tables = [row[0] for row in result.fetchall()]

        if tables:
            table_list = ", ".join(f'"{t}"' for t in tables)
            await db.execute(text(f"TRUNCATE TABLE {table_list} CASCADE"))
            await db.commit()

        logger.info(f"E2E DB reset: truncated {len(tables)} tables")
        return {"detail": "Database reset complete"}
    except Exception:
        logger.error(f"E2E DB reset failed:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database reset failed",
        )


@setup_router.post("/init")
async def setup_init(data: SetupInitRequest, db: AsyncSession = Depends(get_db)):
    """E2E 전용 원스텝 초기 설정 엔드포인트.

    관리자 생성 → 시스템 설정 → 설정 완료를 하나의 요청으로 처리합니다.
    SETUP_TOKEN 없이 호출 가능 (E2E_TESTING=true 환경에서만 등록되므로 안전).

    Args:
        data: 초기 설정 요청 데이터 (관리자 정보 + 앱 이름).
        db: 비동기 DB 세션.

    Returns:
        dict: 설정 완료 메시지.
    """
    try:
        # 1. 관리자 생성
        admin = User(
            email=data.admin_email,
            name=data.admin_name,
            password_hash=await hash_password(data.admin_password),
            is_admin=True,
        )
        db.add(admin)
        await db.flush()

        # 2. 시스템 설정 저장
        if data.app_name:
            db.add(SystemSetting(key="app_name", value=data.app_name))

        # 3. 설정 완료 마킹
        db.add(SystemSetting(key="setup_completed", value="true"))

        await db.commit()
        logger.info(f"E2E setup init complete: admin={data.admin_email}")
        return {"detail": "Setup completed"}
    except Exception:
        await db.rollback()
        logger.error(f"E2E setup init failed:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Setup init failed",
        )
