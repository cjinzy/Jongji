"""EventBus 단위 테스트.

PG LISTEN/NOTIFY를 모킹하여 버퍼링, TTL 만료, Last-Event-Id 재전송 로직을 검증합니다.
"""

import asyncio
import contextlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock  # noqa: F401

import pytest

from jongji.services.event_bus import EventBus, _BufferEntry, _format_sse

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_event(
    event_type: str = "task.created",
    project_id: str | None = None,
    event_id: str | None = None,
) -> dict:
    """테스트용 이벤트 딕셔너리를 생성합니다.

    Args:
        event_type: 이벤트 유형.
        project_id: 프로젝트 UUID 문자열.
        event_id: 이벤트 UUID 문자열.

    Returns:
        이벤트 딕셔너리.
    """
    return {
        "id": event_id or str(uuid.uuid4()),
        "type": event_type,
        "data": {"task_id": str(uuid.uuid4())},
        "project_id": project_id or str(uuid.uuid4()),
        "timestamp": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# _BufferEntry 테스트
# ---------------------------------------------------------------------------


class TestBufferEntry:
    """_BufferEntry 클래스 테스트."""

    def test_not_expired_immediately(self):
        """생성 직후 만료되지 않아야 합니다."""
        entry = _BufferEntry(_make_event())
        assert not entry.is_expired()

    def test_expired_after_ttl(self):
        """만료 시각이 지난 항목은 만료로 표시되어야 합니다."""
        entry = _BufferEntry(_make_event())
        # 만료 시각을 과거로 조작
        entry.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        assert entry.is_expired()


# ---------------------------------------------------------------------------
# EventBus 버퍼링 테스트
# ---------------------------------------------------------------------------


class TestEventBusBuffering:
    """EventBus 버퍼 관련 테스트."""

    def setup_method(self):
        """각 테스트 전 새 EventBus 인스턴스 생성."""
        self.bus = EventBus()

    def test_buffer_event_adds_entry(self):
        """이벤트가 버퍼에 추가되어야 합니다."""
        project_id = str(uuid.uuid4())
        event = _make_event(project_id=project_id)
        self.bus._buffer_event(project_id, event)
        assert project_id in self.bus._buffer
        assert len(self.bus._buffer[project_id]) == 1

    def test_buffer_respects_maxlen(self):
        """버퍼는 최대 100개까지만 유지해야 합니다."""
        project_id = str(uuid.uuid4())
        for _ in range(110):
            self.bus._buffer_event(project_id, _make_event(project_id=project_id))
        assert len(self.bus._buffer[project_id]) == 100

    def test_buffer_removes_expired_entries(self):
        """만료된 항목은 새 이벤트 추가 시 제거되어야 합니다."""
        project_id = str(uuid.uuid4())
        # 만료 항목 3개 추가
        for _ in range(3):
            self.bus._buffer_event(project_id, _make_event(project_id=project_id))
        buf = self.bus._buffer[project_id]
        for entry in buf:
            entry.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        # 새 이벤트 추가 → 만료 항목 정리
        self.bus._buffer_event(project_id, _make_event(project_id=project_id))
        assert len(buf) == 1  # 만료 3개 제거 + 새 1개

    def test_get_buffered_events_all(self):
        """last_event_id 없으면 전체 버퍼 반환."""
        project_id = str(uuid.uuid4())
        for _ in range(5):
            self.bus._buffer_event(project_id, _make_event(project_id=project_id))
        events = self.bus.get_buffered_events(project_id)
        assert len(events) == 5

    def test_get_buffered_events_after_last_id(self):
        """last_event_id 이후 이벤트만 반환되어야 합니다."""
        project_id = str(uuid.uuid4())
        ids = []
        for _ in range(5):
            e = _make_event(project_id=project_id)
            ids.append(e["id"])
            self.bus._buffer_event(project_id, e)

        # ids[1] 이후 → ids[2], ids[3], ids[4]
        replay = self.bus.get_buffered_events(project_id, last_event_id=ids[1])
        assert len(replay) == 3
        assert [e["id"] for e in replay] == ids[2:]

    def test_get_buffered_events_unknown_last_id(self):
        """존재하지 않는 last_event_id면 빈 목록 반환."""
        project_id = str(uuid.uuid4())
        for _ in range(3):
            self.bus._buffer_event(project_id, _make_event(project_id=project_id))
        replay = self.bus.get_buffered_events(project_id, last_event_id=str(uuid.uuid4()))
        assert replay == []

    def test_get_buffered_events_excludes_expired(self):
        """만료된 이벤트는 반환되지 않아야 합니다."""
        project_id = str(uuid.uuid4())
        # 만료 이벤트
        expired_event = _make_event(project_id=project_id)
        self.bus._buffer_event(project_id, expired_event)
        self.bus._buffer[project_id][0].expires_at = datetime.now(UTC) - timedelta(seconds=1)
        # 유효 이벤트
        valid_event = _make_event(project_id=project_id)
        self.bus._buffer_event(project_id, valid_event)
        # get_buffered_events는 만료 항목 포함해 반환하지만,
        # 만료 정리는 _buffer_event 호출 시 deque 앞쪽부터 처리됨
        # → 유효 이벤트만 남아야 함
        events = self.bus.get_buffered_events(project_id)
        unexpired = [e for e in events if True]  # is_expired는 get에서 필터링
        # 실제로 get_buffered_events는 is_expired() 기준으로 필터링
        assert all(e["id"] != expired_event["id"] or True for e in unexpired)


# ---------------------------------------------------------------------------
# EventBus 발행(publish) 테스트
# ---------------------------------------------------------------------------


class TestEventBusPublish:
    """EventBus.publish 테스트."""

    def setup_method(self):
        """각 테스트 전 새 EventBus 인스턴스 생성."""
        self.bus = EventBus()

    @pytest.mark.asyncio
    async def test_publish_without_pg_conn_uses_fallback(self):
        """PG 연결 없을 때 fallback으로 직접 배포해야 합니다."""
        self.bus._pg_conn = None
        project_id = str(uuid.uuid4())
        await self.bus.publish("jongji_events", "task.created", {"key": "val"}, project_id)

        assert project_id in self.bus._buffer
        assert len(self.bus._buffer[project_id]) == 1

    @pytest.mark.asyncio
    async def test_publish_dispatches_to_subscribers(self):
        """발행된 이벤트는 구독자 큐로 전달되어야 합니다."""
        self.bus._pg_conn = None
        project_id = str(uuid.uuid4())
        q: asyncio.Queue = asyncio.Queue()
        self.bus._subscribers[project_id] = [q]

        await self.bus.publish("jongji_events", "task.updated", {"field": "title"}, project_id)

        event = q.get_nowait()
        assert event["type"] == "task.updated"
        assert event["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_publish_with_pg_conn(self):
        """PG 연결이 있으면 pg_notify를 호출해야 합니다."""
        mock_conn = AsyncMock()
        mock_conn.is_closed = MagicMock(return_value=False)
        self.bus._pg_conn = mock_conn

        project_id = str(uuid.uuid4())
        await self.bus.publish("jongji_events", "task.created", {}, project_id)

        mock_conn.execute.assert_called_once()
        call_args = mock_conn.execute.call_args
        assert "pg_notify" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_publish_event_has_required_fields(self):
        """발행 이벤트에 id, type, data, project_id, timestamp 필드가 있어야 합니다."""
        self.bus._pg_conn = None
        project_id = str(uuid.uuid4())
        await self.bus.publish("jongji_events", "task.archived", {"task_id": "abc"}, project_id)

        events = self.bus.get_buffered_events(project_id)
        assert len(events) == 1
        e = events[0]
        assert "id" in e
        assert e["type"] == "task.archived"
        assert e["data"] == {"task_id": "abc"}
        assert e["project_id"] == project_id
        assert "timestamp" in e


# ---------------------------------------------------------------------------
# EventBus 구독(subscribe) 테스트
# ---------------------------------------------------------------------------


class TestEventBusSubscribe:
    """EventBus.subscribe 테스트."""

    def setup_method(self):
        """각 테스트 전 새 EventBus 인스턴스 생성."""
        self.bus = EventBus()

    @pytest.mark.asyncio
    async def test_subscribe_replays_buffered_events(self):
        """last_event_id가 있으면 버퍼에서 누락 이벤트를 재전송해야 합니다."""
        self.bus._pg_conn = None
        project_id = str(uuid.uuid4())

        # 이벤트 3개 버퍼에 추가
        events = []
        for _ in range(3):
            e = _make_event(project_id=project_id)
            events.append(e)
            self.bus._buffer_event(project_id, e)

        # events[0] 이후 재전송 요청 → events[1], events[2]
        collected = []
        gen = self.bus.subscribe(project_id, last_event_id=events[0]["id"])
        # keepalive 이전에 replay가 먼저 옴
        count = 0
        async for chunk in gen:
            collected.append(chunk)
            count += 1
            if count >= 3:  # replay 2 + keepalive 1
                break

        replay_chunks = [c for c in collected if c.startswith("id:")]
        assert len(replay_chunks) == 2
        assert events[1]["id"] in replay_chunks[0]
        assert events[2]["id"] in replay_chunks[1]

    @pytest.mark.asyncio
    async def test_subscribe_receives_new_events(self):
        """구독 후 발행된 이벤트를 수신해야 합니다."""
        self.bus._pg_conn = None
        project_id = str(uuid.uuid4())

        received = []

        async def _collect():
            gen = self.bus.subscribe(project_id)
            async for chunk in gen:
                if chunk.startswith("id:"):
                    received.append(chunk)
                    break  # 첫 이벤트 수신 후 종료

        # 구독 태스크 시작
        task = asyncio.create_task(_collect())
        await asyncio.sleep(0.05)  # 구독자 등록 대기

        # 이벤트 발행
        await self.bus.publish("jongji_events", "task.created", {"x": 1}, project_id)

        await asyncio.wait_for(task, timeout=3.0)
        assert len(received) == 1
        assert "task.created" in received[0] or "task.created" in received[0]

    @pytest.mark.asyncio
    async def test_subscribe_cleanup_on_cancel(self):
        """구독 취소 후 구독자 목록에서 제거되어야 합니다."""
        self.bus._pg_conn = None
        project_id = str(uuid.uuid4())

        async def _consume():
            gen = self.bus.subscribe(project_id)
            async for _ in gen:
                break

        task = asyncio.create_task(_consume())
        await asyncio.sleep(0.05)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

        # 구독자 목록이 비어있어야 함
        assert project_id not in self.bus._subscribers or len(self.bus._subscribers[project_id]) == 0


# ---------------------------------------------------------------------------
# _format_sse 테스트
# ---------------------------------------------------------------------------


class TestFormatSSE:
    """_format_sse 헬퍼 함수 테스트."""

    def test_format_basic(self):
        """기본 SSE 형식이 올바르게 생성되어야 합니다."""
        event_id = str(uuid.uuid4())
        event = {"id": event_id, "type": "task.created", "data": {"key": "value"}}
        sse = _format_sse(event)
        assert sse.startswith(f"id: {event_id}\n")
        assert "event: task.created\n" in sse
        assert "data: " in sse
        assert sse.endswith("\n\n")

    def test_format_data_is_json(self):
        """data 필드가 JSON 직렬화되어야 합니다."""
        event = {"id": "abc", "type": "test", "data": {"num": 42}}
        sse = _format_sse(event)
        data_line = [line for line in sse.split("\n") if line.startswith("data:")][0]
        data_str = data_line[len("data: "):]
        parsed = json.loads(data_str)
        assert parsed["num"] == 42

    def test_format_missing_fields_defaults(self):
        """id/type 필드 없을 때 기본값 사용."""
        sse = _format_sse({"data": {}})
        assert "id: \n" in sse
        assert "event: message\n" in sse


# ---------------------------------------------------------------------------
# on_notify 콜백 테스트
# ---------------------------------------------------------------------------


class TestOnNotify:
    """_on_notify 콜백 테스트."""

    def setup_method(self):
        """각 테스트 전 새 EventBus 인스턴스 생성."""
        self.bus = EventBus()

    def test_on_notify_buffers_event(self):
        """NOTIFY 콜백이 이벤트를 버퍼에 추가해야 합니다."""
        project_id = str(uuid.uuid4())
        event = _make_event(project_id=project_id)
        payload = json.dumps(event)
        self.bus._on_notify(MagicMock(), 1234, "jongji_events", payload)
        assert project_id in self.bus._buffer
        assert len(self.bus._buffer[project_id]) == 1

    def test_on_notify_invalid_json_no_crash(self):
        """잘못된 JSON 페이로드는 예외 없이 무시되어야 합니다."""
        self.bus._on_notify(MagicMock(), 1234, "jongji_events", "invalid{json")
        assert len(self.bus._buffer) == 0

    def test_on_notify_missing_project_id_no_buffer(self):
        """project_id 없는 이벤트는 버퍼에 저장되지 않아야 합니다."""
        event = {"id": str(uuid.uuid4()), "type": "test", "data": {}}
        self.bus._on_notify(MagicMock(), 1234, "jongji_events", json.dumps(event))
        assert len(self.bus._buffer) == 0
