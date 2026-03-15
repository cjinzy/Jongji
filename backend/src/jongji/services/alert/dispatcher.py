"""알림 디스패처 모듈.

이벤트 발생 시 수신자를 결정하고, DND 필터링 후 alert_logs에 저장합니다.
"""

import re
import uuid
from datetime import UTC, datetime, time

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.alert import AlertConfig, AlertLog
from jongji.models.enums import AlertLogStatus
from jongji.models.task import Task, TaskWatcher
from jongji.models.user import User


def _is_in_dnd(user: User, now_time: time) -> bool:
    """사용자가 현재 DND(방해 금지) 시간대에 있는지 확인합니다.

    Args:
        user: 사용자 모델 인스턴스.
        now_time: 현재 시각(time 객체).

    Returns:
        DND 활성화 여부.
    """
    if user.dnd_start is None or user.dnd_end is None:
        return False

    start = user.dnd_start
    end = user.dnd_end

    # 자정을 넘기는 경우 (예: 22:00 ~ 08:00)
    if start > end:
        return now_time >= start or now_time < end
    # 같은 날 범위 (예: 01:00 ~ 07:00)
    return start <= now_time < end


def _extract_mentioned_user_ids(text: str | None) -> list[str]:
    """댓글/설명에서 @멘션된 사용자 ID를 추출합니다.

    Args:
        text: 검색할 텍스트.

    Returns:
        멘션된 사용자 ID 문자열 목록.
    """
    if not text:
        return []
    # @<uuid> 패턴 추출
    pattern = r"@([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    return re.findall(pattern, text, re.IGNORECASE)


async def dispatch(
    event_type: str,
    task: Task,
    actor_user: User,
    db: AsyncSession,
) -> list[AlertLog]:
    """이벤트 발생 시 알림을 생성하고 alert_logs에 저장합니다.

    수신자를 결정하는 우선순위:
    1. 작업 생성자 (creator)
    2. 작업 담당자 (assignee)
    3. 작업 감시자 (watchers)
    4. 설명/댓글에서 @멘션된 사용자

    DND 시간대에 있는 사용자는 스킵하며, 이벤트 유발자(actor)는 수신자에서 제외됩니다.

    Args:
        event_type: 이벤트 유형 (예: 'task_created', 'task_updated').
        task: 이벤트가 발생한 Task 객체.
        actor_user: 이벤트를 유발한 사용자.
        db: 비동기 DB 세션.

    Returns:
        생성된 AlertLog 객체 목록.
    """
    try:
        now_time = datetime.now(UTC).time()

        # 수신자 UUID 집합 수집
        recipient_ids: set[uuid.UUID] = set()

        # creator
        if task.creator_id != actor_user.id:
            recipient_ids.add(task.creator_id)

        # assignee
        if task.assignee_id and task.assignee_id != actor_user.id:
            recipient_ids.add(task.assignee_id)

        # watchers
        watcher_rows = await db.execute(
            select(TaskWatcher.user_id).where(TaskWatcher.task_id == task.id)
        )
        for watcher_user_id in watcher_rows.scalars().all():
            if watcher_user_id != actor_user.id:
                recipient_ids.add(watcher_user_id)

        # @멘션된 사용자 (최근 댓글에서 추출)
        mentioned_ids = _extract_mentioned_user_ids(task.description)
        for uid_str in mentioned_ids:
            try:
                uid = uuid.UUID(uid_str)
                if uid != actor_user.id:
                    recipient_ids.add(uid)
            except ValueError:
                pass

        if not recipient_ids:
            logger.debug(f"dispatch: 수신자 없음 event_type={event_type} task={task.id}")
            return []

        # 수신자 사용자 정보 조회
        users_result = await db.execute(
            select(User).where(User.id.in_(recipient_ids))
        )
        users: list[User] = list(users_result.scalars().all())

        # alert_configs 조회 (활성화된 채널)
        configs_result = await db.execute(
            select(AlertConfig).where(
                AlertConfig.user_id.in_(recipient_ids),
                AlertConfig.is_enabled.is_(True),
            )
        )
        configs = configs_result.scalars().all()
        # user_id -> [AlertConfig] 맵
        user_configs: dict[uuid.UUID, list[AlertConfig]] = {}
        for cfg in configs:
            user_configs.setdefault(cfg.user_id, []).append(cfg)

        created_logs: list[AlertLog] = []
        user_map: dict[uuid.UUID, User] = {u.id: u for u in users}

        for uid in recipient_ids:
            user = user_map.get(uid)
            if user is None:
                continue

            # DND 필터링
            if _is_in_dnd(user, now_time):
                logger.debug(f"dispatch: DND 스킵 user={uid}")
                continue

            channels = user_configs.get(uid, [])
            # 채널 설정이 없어도 이메일 기본값으로 pending 로그 생성
            channels_to_log = [("email", None)] if not channels else [(cfg.channel, cfg) for cfg in channels]

            for channel_name, cfg in channels_to_log:
                payload: dict = {
                    "event_type": event_type,
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "actor": actor_user.name,
                    "recipient_email": user.email,
                }
                if cfg is not None:
                    payload["webhook_url"] = cfg.webhook_url
                    payload["chat_id"] = cfg.chat_id

                log = AlertLog(
                    user_id=uid,
                    channel=str(channel_name),
                    status=AlertLogStatus.PENDING,
                    retry_count=0,
                    payload=payload,
                    task_id=task.id,
                    event_type=event_type,
                )
                db.add(log)
                created_logs.append(log)

        await db.flush()
        logger.info(
            f"dispatch: {len(created_logs)}개 AlertLog 생성 "
            f"event_type={event_type} task={task.id}"
        )
        return created_logs

    except Exception:
        logger.exception(
            f"dispatch 오류: event_type={event_type} task={task.id}"
        )
        return []
