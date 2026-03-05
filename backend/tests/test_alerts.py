"""알림 시스템 테스트.

AlertDispatcher 수신자 결정, DND 필터링, 다이제스트 그룹핑,
채널 전송 모킹, RSS 피드 XML 생성을 검증합니다.
"""

import uuid
from dataclasses import dataclass, field
from datetime import time
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from jongji.models.enums import AlertLogStatus, TaskStatus, TeamRole
from jongji.models.project import Project
from jongji.models.task import Task, TaskWatcher
from jongji.models.team import Team, TeamMember
from jongji.models.user import User
from jongji.services.alert.digest import _build_digest_message
from jongji.services.alert.dispatcher import _is_in_dnd, dispatch

# ---------------------------------------------------------------------------
# 더미 객체 (SQLAlchemy 인스턴스화 없이 단위 테스트에 사용)
# ---------------------------------------------------------------------------


@dataclass
class DummyUser:
    """단위 테스트용 더미 사용자 객체."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: str = "dummy@example.com"
    name: str = "Dummy"
    dnd_start: time | None = None
    dnd_end: time | None = None


@dataclass
class DummyLog:
    """단위 테스트용 더미 AlertLog 객체."""

    payload: dict = field(default_factory=dict)


@dataclass
class DummyProject:
    """단위 테스트용 더미 Project 객체."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = "더미 프로젝트"
    description: str | None = None


# ---------------------------------------------------------------------------
# DB 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
async def user_alice(db_session):
    """테스트용 사용자 Alice를 생성합니다."""
    user = User(
        email=f"alice-{uuid.uuid4().hex[:6]}@example.com",
        name="Alice",
        password_hash="hash",
        dnd_start=None,
        dnd_end=None,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def user_bob(db_session):
    """테스트용 사용자 Bob을 생성합니다."""
    user = User(
        email=f"bob-{uuid.uuid4().hex[:6]}@example.com",
        name="Bob",
        password_hash="hash",
        dnd_start=None,
        dnd_end=None,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def team(db_session, user_alice):
    """테스트용 팀을 생성합니다."""
    t = Team(
        name=f"Test Team {uuid.uuid4().hex[:6]}",
        created_by=user_alice.id,
    )
    db_session.add(t)
    await db_session.flush()
    member = TeamMember(team_id=t.id, user_id=user_alice.id, role=TeamRole.LEADER)
    db_session.add(member)
    await db_session.flush()
    return t


@pytest.fixture
async def project(db_session, team, user_alice):
    """테스트용 프로젝트를 생성합니다."""
    proj = Project(
        team_id=team.id,
        name=f"Test Project {uuid.uuid4().hex[:6]}",
        key=f"TP{uuid.uuid4().hex[:4].upper()}",
        description="테스트 프로젝트",
        owner_id=user_alice.id,
        task_counter=0,
    )
    db_session.add(proj)
    await db_session.flush()
    return proj


@pytest.fixture
async def task(db_session, project, user_alice, user_bob):
    """테스트용 작업을 생성합니다 (creator=alice, assignee=bob)."""
    t = Task(
        project_id=project.id,
        number=1,
        title="테스트 작업",
        description="작업 설명",
        status=TaskStatus.TODO,
        priority=5,
        creator_id=user_alice.id,
        assignee_id=user_bob.id,
    )
    db_session.add(t)
    await db_session.flush()
    return t


# ---------------------------------------------------------------------------
# 1. DND 윈도우 필터링 (순수 단위 테스트, DB 불필요)
# ---------------------------------------------------------------------------


class TestIsDnd:
    """_is_in_dnd 함수 단위 테스트."""

    def test_no_dnd_configured(self):
        """DND 미설정 시 항상 False를 반환해야 합니다."""
        user = DummyUser(dnd_start=None, dnd_end=None)
        assert _is_in_dnd(user, time(3, 0)) is False  # type: ignore[arg-type]

    def test_dnd_same_day_inside(self):
        """같은 날 DND 범위 내 시각은 True를 반환해야 합니다."""
        user = DummyUser(dnd_start=time(22, 0), dnd_end=time(23, 59))
        assert _is_in_dnd(user, time(23, 0)) is True  # type: ignore[arg-type]

    def test_dnd_same_day_outside(self):
        """같은 날 DND 범위 밖 시각은 False를 반환해야 합니다."""
        user = DummyUser(dnd_start=time(22, 0), dnd_end=time(23, 59))
        assert _is_in_dnd(user, time(10, 0)) is False  # type: ignore[arg-type]

    def test_dnd_midnight_crossing_inside_before_midnight(self):
        """자정을 넘는 DND: 자정 이전 시각은 True를 반환해야 합니다."""
        user = DummyUser(dnd_start=time(22, 0), dnd_end=time(8, 0))
        assert _is_in_dnd(user, time(23, 0)) is True  # type: ignore[arg-type]

    def test_dnd_midnight_crossing_inside_after_midnight(self):
        """자정을 넘는 DND: 자정 이후 시각은 True를 반환해야 합니다."""
        user = DummyUser(dnd_start=time(22, 0), dnd_end=time(8, 0))
        assert _is_in_dnd(user, time(3, 0)) is True  # type: ignore[arg-type]

    def test_dnd_midnight_crossing_outside(self):
        """자정을 넘는 DND: 범위 밖 시각은 False를 반환해야 합니다."""
        user = DummyUser(dnd_start=time(22, 0), dnd_end=time(8, 0))
        assert _is_in_dnd(user, time(12, 0)) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 2. AlertDispatcher 수신자 결정
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_creates_logs_for_assignee(db_session, user_alice, user_bob, task):
    """dispatch: assignee(bob)에게 알림 로그를 생성해야 합니다.

    actor가 alice이므로 alice는 제외, bob만 로그 생성.
    """
    logs = await dispatch(
        event_type="task_updated",
        task=task,
        actor_user=user_alice,
        db=db_session,
    )
    assert len(logs) >= 1
    user_ids = {log.user_id for log in logs}
    assert user_bob.id in user_ids
    assert user_alice.id not in user_ids


@pytest.mark.asyncio
async def test_dispatch_includes_watcher(db_session, user_alice, user_bob, task):
    """dispatch: watcher는 알림 수신자에 포함되어야 합니다."""
    watcher = TaskWatcher(task_id=task.id, user_id=user_alice.id)
    db_session.add(watcher)
    await db_session.flush()

    logs = await dispatch(
        event_type="task_commented",
        task=task,
        actor_user=user_bob,
        db=db_session,
    )
    user_ids = {log.user_id for log in logs}
    assert user_alice.id in user_ids


@pytest.mark.asyncio
async def test_dispatch_skips_dnd_user(db_session, user_alice, user_bob, task):
    """dispatch: DND 시간대의 사용자는 알림에서 제외되어야 합니다."""
    user_bob.dnd_start = time(0, 0)
    user_bob.dnd_end = time(23, 59)
    await db_session.flush()

    logs = await dispatch(
        event_type="task_updated",
        task=task,
        actor_user=user_alice,
        db=db_session,
    )
    user_ids = {log.user_id for log in logs}
    assert user_bob.id not in user_ids


@pytest.mark.asyncio
async def test_dispatch_saves_pending_status(db_session, user_alice, user_bob, task):
    """dispatch: 생성된 AlertLog의 초기 상태는 PENDING이어야 합니다."""
    logs = await dispatch(
        event_type="task_created",
        task=task,
        actor_user=user_alice,
        db=db_session,
    )
    for log in logs:
        assert log.status == AlertLogStatus.PENDING


# ---------------------------------------------------------------------------
# 3. 다이제스트 그룹핑 로직 (순수 단위 테스트)
# ---------------------------------------------------------------------------


class TestBuildDigestMessage:
    """_build_digest_message 함수 단위 테스트."""

    def _make_log(self, event_type: str, task_title: str, actor: str) -> Any:
        """더미 payload를 가진 객체를 생성합니다."""
        log = DummyLog(
            payload={
                "event_type": event_type,
                "task_title": task_title,
                "actor": actor,
            }
        )
        return log

    def test_single_log_digest(self):
        """단일 로그의 다이제스트 메시지가 올바르게 생성되어야 합니다."""
        log = self._make_log("task_updated", "내 작업", "Alice")
        subject, body = _build_digest_message([log])  # type: ignore[arg-type]
        assert "내 작업" in subject
        assert "1건" in subject
        assert "task_updated" in body
        assert "Alice" in body

    def test_multiple_logs_merged(self):
        """여러 로그가 하나의 메시지로 병합되어야 합니다."""
        logs = [
            self._make_log("task_updated", "내 작업", "Alice"),
            self._make_log("task_commented", "내 작업", "Bob"),
        ]
        subject, body = _build_digest_message(logs)  # type: ignore[arg-type]
        assert "2건" in subject
        assert "task_updated" in body
        assert "task_commented" in body

    def test_empty_logs_returns_empty_strings(self):
        """빈 목록 입력 시 빈 문자열을 반환해야 합니다."""
        subject, body = _build_digest_message([])
        assert subject == ""
        assert body == ""


# ---------------------------------------------------------------------------
# 4. 채널 전송 모킹
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_smtp_channel_send_success():
    """SmtpEmailChannel.send: 성공 시 True를 반환해야 합니다."""
    from jongji.services.alert.email import SmtpEmailChannel

    channel = SmtpEmailChannel()
    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None
        result = await channel.send("test@example.com", "제목", "본문")
    assert result is True


@pytest.mark.asyncio
async def test_smtp_channel_send_failure():
    """SmtpEmailChannel.send: 예외 발생 시 False를 반환해야 합니다."""
    from jongji.services.alert.email import SmtpEmailChannel

    channel = SmtpEmailChannel()
    with patch("aiosmtplib.send", new_callable=AsyncMock, side_effect=Exception("연결 실패")):
        result = await channel.send("test@example.com", "제목", "본문")
    assert result is False


@pytest.mark.asyncio
async def test_discord_channel_send_success():
    """DiscordChannel.send: 성공 시 True를 반환해야 합니다."""
    from jongji.services.alert.channels import DiscordChannel

    channel = DiscordChannel(webhook_url="https://discord.com/api/webhooks/test")

    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await channel.send("", "제목", "본문")
    assert result is True


@pytest.mark.asyncio
async def test_telegram_channel_send_success():
    """TelegramChannel.send: 성공 시 True를 반환해야 합니다."""
    from jongji.services.alert.channels import TelegramChannel

    channel = TelegramChannel(bot_token="test_token", chat_id="12345")

    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        result = await channel.send("", "제목", "본문")
    assert result is True


# ---------------------------------------------------------------------------
# 5. RSS 피드 XML 생성
# ---------------------------------------------------------------------------


class TestRssFeedXml:
    """RSS XML 생성 함수 단위 테스트."""

    def test_rss_xml_structure(self):
        """RSS XML이 올바른 구조를 가져야 합니다."""
        from jongji.api.rss import _build_rss_xml

        proj = DummyProject(name="테스트 프로젝트", description="프로젝트 설명")
        items = [
            {
                "title": "작업 변경",
                "link": "/projects/1/tasks/1",
                "description": "상태가 변경되었습니다.",
                "pubDate": "Thu, 01 Jan 2026 00:00:00 +0000",
                "guid": str(uuid.uuid4()),
            }
        ]

        xml_str = _build_rss_xml(proj, items)  # type: ignore[arg-type]
        assert '<?xml version="1.0"' in xml_str
        assert "<rss" in xml_str
        assert "<channel>" in xml_str
        assert "<item>" in xml_str
        assert "테스트 프로젝트" in xml_str
        assert "작업 변경" in xml_str

    def test_rss_xml_empty_items(self):
        """아이템이 없어도 유효한 RSS XML을 생성해야 합니다."""
        from jongji.api.rss import _build_rss_xml

        proj = DummyProject(name="빈 프로젝트", description=None)
        xml_str = _build_rss_xml(proj, [])  # type: ignore[arg-type]
        assert "<channel>" in xml_str
        assert "<item>" not in xml_str

    def test_rss_router_exists(self):
        """RSS 라우터가 등록되어 있어야 합니다."""
        from jongji.api.rss import router

        assert len(router.routes) > 0
