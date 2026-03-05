"""FastAPI 애플리케이션 진입점.

앱 인스턴스 생성, 미들웨어 설정, 라우터 등록을 담당합니다.
"""

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from jongji.api.admin import router as admin_router
from jongji.api.auth import router as auth_router
from jongji.api.health import router as health_router
from jongji.api.setup import router as setup_router
from jongji.api.users import router as users_router
from jongji.config import settings

# loguru JSON 로깅 설정
logger.remove()
logger.add(sys.stderr, format="{time} {level} {message}", serialize=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 수명 주기 관리.

    Args:
        app: FastAPI 애플리케이션 인스턴스.
    """
    logger.info("Starting Jongji server")
    yield
    logger.info("Shutting down Jongji server")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(setup_router, prefix="/api/v1")
app.include_router(users_router)
app.include_router(admin_router)
