"""데이터베이스 모델 생성 및 기본 관계 테스트."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from jongji.models.project import Project
from jongji.models.system import SystemSetting
from jongji.models.task import Task, TaskStatus
from jongji.models.team import Team, TeamMember
from jongji.models.user import User


@pytest.mark.asyncio
async def test_create_user(db_session):
    """필수 필드로 사용자를 생성하고 기본값을 확인한다."""
    user = User(
        email="test@example.com",
        name="Test User",
        password_hash="hashed_password",
    )
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.is_admin is False
    assert user.is_active is True
    assert user.locale == "ko"


@pytest.mark.asyncio
async def test_create_team_with_members(db_session):
    """팀을 생성하고 멤버를 추가한다."""
    user = User(email="leader@example.com", name="Leader")
    db_session.add(user)
    await db_session.flush()

    team = Team(name="Test Team", created_by=user.id)
    db_session.add(team)
    await db_session.flush()

    member = TeamMember(team_id=team.id, user_id=user.id, role="leader")
    db_session.add(member)
    await db_session.flush()

    assert team.id is not None
    assert member.role == "leader"


@pytest.mark.asyncio
async def test_create_project(db_session):
    """팀에 연결된 프로젝트를 생성한다."""
    user = User(email="owner@example.com", name="Owner")
    db_session.add(user)
    await db_session.flush()

    team = Team(name="Dev Team", created_by=user.id)
    db_session.add(team)
    await db_session.flush()

    project = Project(
        team_id=team.id,
        name="Test Project",
        key="TEST",
        owner_id=user.id,
    )
    db_session.add(project)
    await db_session.flush()

    assert project.id is not None
    assert project.task_counter == 0
    assert project.key == "TEST"


@pytest.mark.asyncio
async def test_create_task(db_session):
    """상태와 우선순위를 가진 작업을 생성한다."""
    user = User(email="creator@example.com", name="Creator")
    db_session.add(user)
    await db_session.flush()

    team = Team(name="Team", created_by=user.id)
    db_session.add(team)
    await db_session.flush()

    project = Project(team_id=team.id, name="Proj", key="PRJ", owner_id=user.id)
    db_session.add(project)
    await db_session.flush()

    task = Task(
        project_id=project.id,
        number=1,
        title="First Task",
        status=TaskStatus.BACKLOG,
        priority=5,
        creator_id=user.id,
    )
    db_session.add(task)
    await db_session.flush()

    assert task.id is not None
    assert task.status == TaskStatus.BACKLOG
    assert task.priority == 5


@pytest.mark.asyncio
async def test_system_setting(db_session):
    """시스템 설정 CRUD를 테스트한다."""
    setting = SystemSetting(key="setup_completed", value="false")
    db_session.add(setting)
    await db_session.flush()

    result = await db_session.execute(
        select(SystemSetting).where(SystemSetting.key == "setup_completed")
    )
    s = result.scalar_one()
    assert s.value == "false"


@pytest.mark.asyncio
async def test_unique_project_key(db_session):
    """프로젝트 키의 고유 제약조건을 확인한다."""
    user = User(email="u@example.com", name="U")
    db_session.add(user)
    await db_session.flush()

    team = Team(name="T", created_by=user.id)
    db_session.add(team)
    await db_session.flush()

    p1 = Project(team_id=team.id, name="P1", key="SAME", owner_id=user.id)
    db_session.add(p1)
    await db_session.flush()

    p2 = Project(team_id=team.id, name="P2", key="SAME", owner_id=user.id)
    db_session.add(p2)

    with pytest.raises(IntegrityError):
        await db_session.flush()
