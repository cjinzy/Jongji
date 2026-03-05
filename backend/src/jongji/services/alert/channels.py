"""메시징 플랫폼 알림 채널 구현.

Telegram, Discord, Slack, Google Chat 채널을 httpx를 통해 지원합니다.
"""

import httpx
from loguru import logger

from jongji.services.alert.base import AlertChannel


class TelegramChannel(AlertChannel):
    """Telegram Bot API를 통한 알림 채널."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        """Telegram 채널을 초기화합니다.

        Args:
            bot_token: Telegram Bot 토큰.
            chat_id: 메시지를 보낼 채팅 ID.
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    async def send(self, recipient: str, subject: str, body: str) -> bool:
        """Telegram으로 메시지를 전송합니다.

        Args:
            recipient: 사용 안 함 (chat_id가 초기화 시 지정됨).
            subject: 메시지 제목 (본문 앞에 굵게 표시).
            body: 메시지 본문.

        Returns:
            전송 성공 여부.
        """
        try:
            text = f"*{subject}*\n\n{body}"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
            logger.info(f"Telegram 메시지 전송 성공: chat_id={self.chat_id}")
            return True
        except Exception:
            logger.exception(f"Telegram 메시지 전송 실패: chat_id={self.chat_id}")
            return False


class DiscordChannel(AlertChannel):
    """Discord Webhook을 통한 알림 채널."""

    def __init__(self, webhook_url: str) -> None:
        """Discord 채널을 초기화합니다.

        Args:
            webhook_url: Discord 웹훅 URL.
        """
        self.webhook_url = webhook_url

    async def send(self, recipient: str, subject: str, body: str) -> bool:
        """Discord 웹훅으로 메시지를 전송합니다.

        Args:
            recipient: 사용 안 함 (webhook_url이 초기화 시 지정됨).
            subject: 메시지 제목.
            body: 메시지 본문.

        Returns:
            전송 성공 여부.
        """
        try:
            content = f"**{subject}**\n\n{body}"
            payload = {"content": content}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
            logger.info(f"Discord 메시지 전송 성공: {self.webhook_url}")
            return True
        except Exception:
            logger.exception(f"Discord 메시지 전송 실패: {self.webhook_url}")
            return False


class SlackChannel(AlertChannel):
    """Slack Incoming Webhook을 통한 알림 채널."""

    def __init__(self, webhook_url: str) -> None:
        """Slack 채널을 초기화합니다.

        Args:
            webhook_url: Slack 웹훅 URL.
        """
        self.webhook_url = webhook_url

    async def send(self, recipient: str, subject: str, body: str) -> bool:
        """Slack 웹훅으로 메시지를 전송합니다.

        Args:
            recipient: 사용 안 함 (webhook_url이 초기화 시 지정됨).
            subject: 메시지 제목.
            body: 메시지 본문.

        Returns:
            전송 성공 여부.
        """
        try:
            text = f"*{subject}*\n\n{body}"
            payload = {"text": text}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
            logger.info(f"Slack 메시지 전송 성공: {self.webhook_url}")
            return True
        except Exception:
            logger.exception(f"Slack 메시지 전송 실패: {self.webhook_url}")
            return False


class GoogleChatChannel(AlertChannel):
    """Google Chat Webhook을 통한 알림 채널."""

    def __init__(self, webhook_url: str) -> None:
        """Google Chat 채널을 초기화합니다.

        Args:
            webhook_url: Google Chat 웹훅 URL.
        """
        self.webhook_url = webhook_url

    async def send(self, recipient: str, subject: str, body: str) -> bool:
        """Google Chat 웹훅으로 메시지를 전송합니다.

        Args:
            recipient: 사용 안 함 (webhook_url이 초기화 시 지정됨).
            subject: 메시지 제목.
            body: 메시지 본문.

        Returns:
            전송 성공 여부.
        """
        try:
            text = f"*{subject}*\n\n{body}"
            payload = {"text": text}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
            logger.info(f"Google Chat 메시지 전송 성공: {self.webhook_url}")
            return True
        except Exception:
            logger.exception(f"Google Chat 메시지 전송 실패: {self.webhook_url}")
            return False
