"""FastAPI 애플리케이션 진입점.

앱 인스턴스 생성, 미들웨어 설정, 라우터 등록을 담당합니다.
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from jongji.api.admin import router as admin_router
from jongji.api.attachments import router as attachments_router
from jongji.api.audit import router as audit_router
from jongji.api.auth import router as auth_router
from jongji.api.comments import router as comments_router
from jongji.api.dashboard import router as dashboard_router
from jongji.api.events import router as events_router
from jongji.api.export import router as export_router
from jongji.api.health import router as health_router
from jongji.api.invites import router as invites_router
from jongji.api.labels import router as labels_router
from jongji.api.projects import router as projects_router
from jongji.api.rss import router as rss_router
from jongji.api.search import router as search_router
from jongji.api.sessions import router as sessions_router
from jongji.api.setup import router as setup_router
from jongji.api.tags import router as tags_router
from jongji.api.tasks import router as tasks_router
from jongji.api.teams import router as teams_router
from jongji.api.templates import router as templates_router
from jongji.api.users import router as users_router
from jongji.config import settings
from jongji.mcp.tools import mcp
from jongji.services.alert.scheduler import start_scheduler, stop_scheduler

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
    start_scheduler()
    yield
    stop_scheduler()
    logger.info("Shutting down Jongji server")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(audit_router)
app.include_router(sessions_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(setup_router, prefix="/api/v1")
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(teams_router)
app.include_router(invites_router)
app.include_router(projects_router)
app.include_router(labels_router)
app.include_router(tasks_router)
app.include_router(tags_router)
app.include_router(comments_router)
app.include_router(templates_router)
app.include_router(events_router)
app.include_router(search_router)
app.include_router(rss_router)
app.include_router(attachments_router)
app.include_router(export_router)
app.include_router(dashboard_router)
app.mount("/mcp", mcp.http_app())

# E2E 테스트 전용 라우터 (E2E_TESTING=true일 때만 활성화)
if os.environ.get("E2E_TESTING") == "true":
    from jongji.api.testing import router as testing_router

    app.include_router(testing_router, prefix="/api/v1")
    logger.warning("E2E testing endpoints enabled — DO NOT use in production")
