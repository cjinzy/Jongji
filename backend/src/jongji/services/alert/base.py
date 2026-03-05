"""알림 채널 추상 기반 클래스."""

from abc import ABC, abstractmethod


class AlertChannel(ABC):
    """알림 채널 추상 기반 클래스.

    모든 알림 채널(이메일, 텔레그램, 디스코드 등)이 구현해야 하는 인터페이스입니다.
    """

    @abstractmethod
    async def send(self, recipient: str, subject: str, body: str) -> bool:
        """알림을 전송합니다.

        Args:
            recipient: 수신자 식별자 (이메일 주소, chat_id, webhook URL 등).
            subject: 알림 제목.
            body: 알림 본문.

        Returns:
            전송 성공 여부.
        """
        ...
