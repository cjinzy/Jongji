"""SSE EventBus 서비스 모듈.

PostgreSQL LISTEN/NOTIFY를 사용하여 실시간 이벤트를 브로드캐스트하고
SSE(Server-Sent Events) 스트림을 통해 클라이언트에게 전달합니다.
"""

import asyncio
import json
import traceback
import uuid
from collections import deque
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import asyncpg
from loguru import logger

from jongji.config import settings

# 버퍼 설정
_BUFFER_MAX_LEN = 100
_BUFFER_TTL_SECONDS = 300  # 5분


class _BufferEntry:
    """버퍼 항목 (이벤트 + 만료 시각)."""

    __slots__ = ("event", "expires_at")

    def __init__(self, event: dict) -> None:
        """초기화.

        Args:
            event: 이벤트 딕셔너리.
        """
        self.event = event
        self.expires_at = datetime.now(UTC) + timedelta(seconds=_BUFFER_TTL_SECONDS)

    def is_expired(self) -> bool:
        """만료 여부를 반환합니다."""
        return datetime.now(UTC) > self.expires_at


class EventBus:
    """PostgreSQL LISTEN/NOTIFY 기반 SSE 이벤트 버스.

    Attributes:
        _channel: PG NOTIFY 채널 이름.
        _buffer: 프로젝트별 이벤트 버퍼 {project_id: deque}.
        _subscribers: 프로젝트별 구독자 큐 목록 {project_id: list[asyncio.Queue]}.
        _pg_conn: asyncpg 연결.
        _listen_task: 백그라운드 LISTEN 태스크.
    """

    def __init__(self) -> None:
        """EventBus 초기화."""
        self._channel: str = "jongji_events"
        self._buffer: dict[str, deque[_BufferEntry]] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._pg_conn: asyncpg.Connection | None = None
        self._listen_task: asyncio.Task | None = None

    async def start_listening(self, channel: str = "jongji_events") -> None:
        """PostgreSQL LISTEN을 시작합니다.

        asyncpg 연결을 생성하고 지정된 채널을 구독합니다.

        Args:
            channel: LISTEN할 PG 채널 이름.
        """
        self._channel = channel
        try:
            # postgresql+asyncpg:// -> asyncpg DSN으로 변환
            dsn = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            self._pg_conn = await asyncpg.connect(dsn)
            await self._pg_conn.add_listener(channel, self._on_notify)
            logger.info(f"EventBus: LISTEN 시작 채널={channel}")
        except Exception:
            logger.error(f"EventBus: LISTEN 시작 실패\n{traceback.format_exc()}")
            raise

    async def stop_listening(self) -> None:
        """PostgreSQL LISTEN을 중지하고 연결을 닫습니다."""
        try:
            if self._pg_conn and not self._pg_conn.is_closed():
                await self._pg_conn.remove_listener(self._channel, self._on_notify)
                await self._pg_conn.close()
                logger.info("EventBus: LISTEN 중지")
        except Exception:
            logger.warning(f"EventBus: LISTEN 중지 중 오류\n{traceback.format_exc()}")

    def _on_notify(
        self,
        connection: asyncpg.Connection,  # noqa: ARG002
        pid: int,  # noqa: ARG002
        channel: str,  # noqa: ARG002
        payload: str,
    ) -> None:
        """PG NOTIFY 수신 콜백.

        Args:
            connection: asyncpg 연결.
            pid: 발신 프로세스 ID.
            channel: 채널 이름.
            payload: JSON 페이로드 문자열.
        """
        try:
            event = json.loads(payload)
            project_id = event.get("project_id")
            if not project_id:
                return
            self._buffer_event(project_id, event)
            self._dispatch_to_subscribers(project_id, event)
        except Exception:
            logger.warning(f"EventBus: NOTIFY 처리 실패\n{traceback.format_exc()}")

    def _buffer_event(self, project_id: str, event: dict) -> None:
        """이벤트를 프로젝트 버퍼에 추가하고 만료된 항목을 정리합니다.

        Args:
            project_id: 프로젝트 UUID 문자열.
            event: 이벤트 딕셔너리.
        """
        if project_id not in self._buffer:
            self._buffer[project_id] = deque(maxlen=_BUFFER_MAX_LEN)

        buf = self._buffer[project_id]
        # 만료 항목 제거
        while buf and buf[0].is_expired():
            buf.popleft()

        buf.append(_BufferEntry(event))

    def _dispatch_to_subscribers(self, project_id: str, event: dict) -> None:
        """구독자 큐에 이벤트를 전달합니다.

        Args:
            project_id: 프로젝트 UUID 문자열.
            event: 이벤트 딕셔너리.
        """
        queues = self._subscribers.get(project_id, [])
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"EventBus: 구독자 큐 가득 참 project_id={project_id}")

    async def publish(
        self,
        channel: str,
        event_type: str,
        data: dict,
        project_id: str,
    ) -> None:
        """PG NOTIFY를 통해 이벤트를 발행합니다.

        Args:
            channel: PG NOTIFY 채널 이름.
            event_type: 이벤트 유형 (예: task.created).
            data: 이벤트 데이터 딕셔너리.
            project_id: 이벤트 대상 프로젝트 UUID 문자열.

        Raises:
            RuntimeError: PG 연결이 없는 경우.
        """
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "data": data,
            "project_id": project_id,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        payload = json.dumps(event, default=str)
        try:
            if self._pg_conn and not self._pg_conn.is_closed():
                await self._pg_conn.execute("SELECT pg_notify($1, $2)", channel, payload)
                logger.debug(f"EventBus: NOTIFY 발행 type={event_type} project={project_id}")
            else:
                # 연결이 없을 때는 직접 버퍼/구독자에게 전달 (테스트/개발 폴백)
                logger.warning("EventBus: PG 연결 없음, 직접 배포 fallback 사용")
                self._buffer_event(project_id, event)
                self._dispatch_to_subscribers(project_id, event)
        except Exception:
            logger.error(f"EventBus: NOTIFY 발행 실패\n{traceback.format_exc()}")
            raise

    def get_buffered_events(
        self, project_id: str, last_event_id: str | None = None
    ) -> list[dict]:
        """버퍼에서 이벤트를 조회합니다.

        last_event_id가 주어진 경우 해당 이벤트 이후의 이벤트만 반환합니다.

        Args:
            project_id: 프로젝트 UUID 문자열.
            last_event_id: 마지막으로 수신한 이벤트 ID (재연결 시 사용).

        Returns:
            재전송할 이벤트 목록.
        """
        buf = self._buffer.get(project_id, deque())
        events = [entry.event for entry in buf if not entry.is_expired()]

        if last_event_id is None:
            return events

        # last_event_id 이후 이벤트만 추출
        found = False
        replay = []
        for event in events:
            if found:
                replay.append(event)
            elif event.get("id") == last_event_id:
                found = True
        return replay

    async def subscribe(
        self, project_id: str, last_event_id: str | None = None
    ) -> AsyncGenerator[str, None]:
        """프로젝트 이벤트를 SSE 형식으로 yield하는 비동기 제너레이터.

        Last-Event-Id가 주어진 경우 버퍼에서 누락된 이벤트를 먼저 재전송합니다.

        Args:
            project_id: 구독할 프로젝트 UUID 문자열.
            last_event_id: 재연결 시 마지막 이벤트 ID.

        Yields:
            SSE 형식 문자열 (id/event/data 블록).
        """
        # 재연결 시 버퍼 재전송
        if last_event_id is not None:
            buffered = self.get_buffered_events(project_id, last_event_id)
            for event in buffered:
                yield _format_sse(event)

        # 구독자 큐 등록
        q: asyncio.Queue[dict] = asyncio.Queue(maxsize=200)
        if project_id not in self._subscribers:
            self._subscribers[project_id] = []
        self._subscribers[project_id].append(q)

        try:
            # keepalive 주석 전송
            yield ": keepalive\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield _format_sse(event)
                except TimeoutError:
                    # 30초마다 keepalive 전송
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            logger.debug(f"EventBus: 구독 취소 project_id={project_id}")
        finally:
            queues = self._subscribers.get(project_id, [])
            if q in queues:
                queues.remove(q)
            if not queues and project_id in self._subscribers:
                del self._subscribers[project_id]


def _format_sse(event: dict) -> str:
    """이벤트 딕셔너리를 SSE 형식 문자열로 변환합니다.

    Args:
        event: id, type, data 키를 포함한 이벤트 딕셔너리.

    Returns:
        SSE 형식 문자열.
    """
    event_id = event.get("id", "")
    event_type = event.get("type", "message")
    data = json.dumps(event.get("data", {}), default=str)
    return f"id: {event_id}\nevent: {event_type}\ndata: {data}\n\n"


# 싱글턴 EventBus 인스턴스
event_bus = EventBus()

__all__ = ["EventBus", "event_bus"]
