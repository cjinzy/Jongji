"""APScheduler 기반 알림 다이제스트 스케줄러.

5분마다 digest 처리를 실행하며, PostgreSQL advisory lock으로
다중 인스턴스 환경에서 중복 실행을 방지합니다.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from jongji.config import settings
from jongji.services.alert.digest import process_digest

_scheduler: AsyncIOScheduler | None = None

# APScheduler advisory lock ID (임의의 고정 정수)
_ADVISORY_LOCK_ID = 7331_0001


async def _run_digest_with_lock(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """PostgreSQL advisory lock을 획득한 후 다이제스트를 처리합니다.

    다중 인스턴스 환경에서 단일 인스턴스만 처리하도록 보장합니다.

    Args:
        session_factory: 비동기 세션 팩토리.
    """
    async with session_factory() as db:
        try:
            # pg_try_advisory_lock: 잠금 획득 실패 시 즉시 False 반환
            lock_result = await db.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": _ADVISORY_LOCK_ID},
            )
            acquired: bool = lock_result.scalar()

            if not acquired:
                logger.debug("digest 스케줄러: advisory lock 획득 실패, 다른 인스턴스가 처리 중")
                return

            try:
                email_backend = "smtp"
                # system_settings에서 email_backend 조회 (옵션)
                try:
                    setting_result = await db.execute(
                        text("SELECT value FROM system_settings WHERE key = 'email_backend'")
                    )
                    row = setting_result.fetchone()
                    if row:
                        email_backend = row[0]
                except Exception:
                    pass

                await process_digest(db, email_backend=email_backend)
            finally:
                await db.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": _ADVISORY_LOCK_ID},
                )
        except Exception:
            logger.exception("digest 스케줄러 실행 오류")


def create_scheduler() -> AsyncIOScheduler:
    """APScheduler 인스턴스를 생성하고 digest 잡을 등록합니다.

    Returns:
        설정된 AsyncIOScheduler 인스턴스.
    """
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _run_digest_with_lock,
        trigger="interval",
        minutes=5,
        args=[session_factory],
        id="alert_digest",
        replace_existing=True,
        max_instances=1,
    )
    return scheduler


def start_scheduler() -> AsyncIOScheduler:
    """스케줄러를 시작하고 전역 인스턴스를 저장합니다.

    Returns:
        시작된 AsyncIOScheduler 인스턴스.
    """
    global _scheduler
    _scheduler = create_scheduler()
    _scheduler.start()
    logger.info("알림 다이제스트 스케줄러 시작 (5분 간격)")
    return _scheduler


def stop_scheduler() -> None:
    """실행 중인 스케줄러를 중지합니다."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("알림 다이제스트 스케줄러 중지")
    _scheduler = None
