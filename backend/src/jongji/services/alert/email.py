"""이메일 알림 채널 구현.

SMTP(aiosmtplib)와 API(httpx, SendGrid/Mailgun 스타일) 두 가지 백엔드를 지원합니다.
시스템 설정의 email_backend 값에 따라 자동으로 선택됩니다.
"""

import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
import httpx
from loguru import logger

from jongji.services.alert.base import AlertChannel


class SmtpEmailChannel(AlertChannel):
    """SMTP를 통한 이메일 알림 채널.

    환경 변수 SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS 를 사용합니다.
    """

    def __init__(self) -> None:
        """SMTP 설정을 환경 변수에서 로드합니다."""
        self.host: str = os.environ.get("SMTP_HOST", "localhost")
        self.port: int = int(os.environ.get("SMTP_PORT", "587"))
        self.user: str = os.environ.get("SMTP_USER", "")
        self.password: str = os.environ.get("SMTP_PASS", "")

    async def send(self, recipient: str, subject: str, body: str) -> bool:
        """SMTP를 통해 이메일을 전송합니다.

        Args:
            recipient: 수신자 이메일 주소.
            subject: 이메일 제목.
            body: 이메일 본문(HTML 또는 텍스트).

        Returns:
            전송 성공 여부.
        """
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.user
            message["To"] = recipient
            message.attach(MIMEText(body, "plain"))

            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=True,
            )
            logger.info(f"SMTP 이메일 전송 성공: {recipient}")
            return True
        except Exception:
            logger.exception(f"SMTP 이메일 전송 실패: {recipient}")
            return False


class ApiEmailChannel(AlertChannel):
    """HTTP API를 통한 이메일 알림 채널 (SendGrid/Mailgun 스타일).

    환경 변수 EMAIL_API_KEY, EMAIL_API_URL, SMTP_USER(발신자) 를 사용합니다.
    """

    def __init__(self) -> None:
        """API 설정을 환경 변수에서 로드합니다."""
        self.api_key: str = os.environ.get("EMAIL_API_KEY", "")
        self.api_url: str = os.environ.get("EMAIL_API_URL", "")
        self.from_email: str = os.environ.get("SMTP_USER", "noreply@example.com")

    async def send(self, recipient: str, subject: str, body: str) -> bool:
        """HTTP API를 통해 이메일을 전송합니다.

        Args:
            recipient: 수신자 이메일 주소.
            subject: 이메일 제목.
            body: 이메일 본문.

        Returns:
            전송 성공 여부.
        """
        try:
            payload = {
                "from": self.from_email,
                "to": recipient,
                "subject": subject,
                "text": body,
            }
            headers = {"Authorization": f"Bearer {self.api_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                response.raise_for_status()

            logger.info(f"API 이메일 전송 성공: {recipient}")
            return True
        except Exception:
            logger.exception(f"API 이메일 전송 실패: {recipient}")
            return False


def get_email_channel(email_backend: str = "smtp") -> AlertChannel:
    """email_backend 설정에 따라 이메일 채널 인스턴스를 반환합니다.

    Args:
        email_backend: 'smtp' 또는 'api'. 기본값은 'smtp'.

    Returns:
        SmtpEmailChannel 또는 ApiEmailChannel 인스턴스.
    """
    if email_backend == "api":
        return ApiEmailChannel()
    return SmtpEmailChannel()
