"""다이제스트 처리 모듈.

pending 상태의 AlertLog를 사용자/작업별로 묶어 단일 메시지로 전송합니다.
전송 실패 시 지수 백오프(1s, 4s, 16s)로 최대 3회 재시도합니다.
"""

import asyncio
import uuid

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from jongji.models.alert import AlertConfig, AlertLog
from jongji.models.enums import AlertChannel, AlertLogStatus
from jongji.models.user import User
from jongji.services.alert.channels import (
    DiscordChannel,
    GoogleChatChannel,
    SlackChannel,
    TelegramChannel,
)
from jongji.services.alert.email import get_email_channel

_MAX_RETRIES = 3
_BACKOFF_BASE = 4  # 4^0=1s, 4^1=4s, 4^2=16s


def _build_digest_message(logs: list[AlertLog]) -> tuple[str, str]:
    """여러 AlertLog를 하나의 다이제스트 메시지로 병합합니다.

    Args:
        logs: 동일 사용자+작업의 AlertLog 목록.

    Returns:
        (subject, body) 튜플.
    """
    if not logs:
        return "", ""

    first = logs[0]
    task_title = first.payload.get("task_title", "작업")

    subject = f"[Jongji] {task_title} 알림 ({len(logs)}건)"
    lines = [f"작업 '{task_title}'에 다음 변경이 있었습니다:", ""]
    for i, log in enumerate(logs, 1):
        actor = log.payload.get("actor", "")
        evt = log.payload.get("event_type", "")
        lines.append(f"  {i}. [{evt}] by {actor}")
    body = "\n".join(lines)
    return subject, body


async def _send_with_retry(
    channel_name: str,
    cfg: AlertConfig | None,
    recipient_email: str,
    subject: str,
    body: str,
    email_backend: str = "smtp",
) -> bool:
    """채널을 통해 메시지를 전송하며 실패 시 지수 백오프로 재시도합니다.

    Args:
        channel_name: 채널 이름 (AlertChannel enum 값).
        cfg: AlertConfig 인스턴스 (웹훅 URL, chat_id 포함).
        recipient_email: 이메일 채널용 수신자 주소.
        subject: 알림 제목.
        body: 알림 본문.
        email_backend: 'smtp' 또는 'api'.

    Returns:
        최종 전송 성공 여부.
    """
    channel_obj = None

    try:
        ch = AlertChannel(channel_name)
    except ValueError:
        ch = None

    if ch == AlertChannel.EMAIL or ch is None:
        channel_obj = get_email_channel(email_backend)
        recipient = recipient_email
    elif ch == AlertChannel.TELEGRAM:
        bot_token = (cfg.config_json or {}).get("bot_token", "") if cfg else ""
        chat_id = cfg.chat_id or "" if cfg else ""
        channel_obj = TelegramChannel(bot_token=bot_token, chat_id=chat_id)
        recipient = chat_id
    elif ch == AlertChannel.DISCORD:
        webhook_url = cfg.webhook_url or "" if cfg else ""
        channel_obj = DiscordChannel(webhook_url=webhook_url)
        recipient = webhook_url
    elif ch == AlertChannel.SLACK:
        webhook_url = cfg.webhook_url or "" if cfg else ""
        channel_obj = SlackChannel(webhook_url=webhook_url)
        recipient = webhook_url
    elif ch == AlertChannel.GOOGLE_CHAT:
        webhook_url = cfg.webhook_url or "" if cfg else ""
        channel_obj = GoogleChatChannel(webhook_url=webhook_url)
        recipient = webhook_url
    else:
        channel_obj = get_email_channel(email_backend)
        recipient = recipient_email

    for attempt in range(_MAX_RETRIES):
        success = await channel_obj.send(recipient, subject, body)
        if success:
            return True
        if attempt < _MAX_RETRIES - 1:
            delay = _BACKOFF_BASE**attempt  # 1, 4, 16
            logger.warning(
                f"전송 실패, {delay}초 후 재시도 (attempt={attempt + 1}): "
                f"channel={channel_name} recipient={recipient}"
            )
            await asyncio.sleep(delay)

    return False


async def process_digest(db: AsyncSession, email_backend: str = "smtp") -> int:
    """pending 상태 AlertLog를 처리하여 다이제스트 메시지로 전송합니다.

    동일 사용자 + 동일 작업의 알림을 하나로 묶어 전송하며,
    성공 시 status='sent', 실패 시 status='failed'로 업데이트합니다.

    Args:
        db: 비동기 DB 세션.
        email_backend: 이메일 백엔드 ('smtp' 또는 'api').

    Returns:
        처리된 AlertLog 수.
    """
    try:
        # pending 로그 조회
        result = await db.execute(
            select(AlertLog).where(AlertLog.status == AlertLogStatus.PENDING)
        )
        pending_logs: list[AlertLog] = list(result.scalars().all())

        if not pending_logs:
            logger.debug("process_digest: pending 알림 없음")
            return 0

        # user_id + task_id + channel 기준으로 그룹핑
        groups: dict[tuple[uuid.UUID, str | None, str], list[AlertLog]] = {}
        for log in pending_logs:
            key = (log.user_id, str(log.task_id) if log.task_id else None, log.channel)
            groups.setdefault(key, []).append(log)

        # 사용자 정보 일괄 조회
        user_ids = {log.user_id for log in pending_logs}
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        user_map: dict[uuid.UUID, User] = {u.id: u for u in users_result.scalars().all()}

        # AlertConfig 일괄 조회
        configs_result = await db.execute(
            select(AlertConfig).where(
                AlertConfig.user_id.in_(user_ids),
                AlertConfig.is_enabled.is_(True),
            )
        )
        config_map: dict[tuple[uuid.UUID, str], AlertConfig] = {}
        for cfg in configs_result.scalars().all():
            config_map[(cfg.user_id, str(cfg.channel))] = cfg

        processed_count = 0

        for (uid, _task_id_str, channel_name), group_logs in groups.items():
            user = user_map.get(uid)
            if user is None:
                continue

            cfg = config_map.get((uid, channel_name))
            subject, body = _build_digest_message(group_logs)
            recipient_email = user.email

            success = await _send_with_retry(
                channel_name=channel_name,
                cfg=cfg,
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                email_backend=email_backend,
            )

            new_status = AlertLogStatus.SENT if success else AlertLogStatus.FAILED
            log_ids = [log.id for log in group_logs]

            await db.execute(
                update(AlertLog)
                .where(AlertLog.id.in_(log_ids))
                .values(
                    status=new_status,
                    retry_count=AlertLog.retry_count + 1,
                    error_message=None if success else "최대 재시도 횟수 초과",
                )
            )
            processed_count += len(group_logs)

        await db.commit()
        logger.info(f"process_digest: {processed_count}개 알림 처리 완료")
        return processed_count

    except Exception:
        await db.rollback()
        logger.exception("process_digest 오류")
        return 0
