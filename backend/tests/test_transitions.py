"""작업 상태 전환 및 blocked_by 관계 테스트 - TDD 방식.

상태 전환 유효성 검사, blocked_by 제약, 사이클 감지를 테스트합니다.
ORM으로 직접 사용자를 생성하고 JWT를 발급하여 auth 의존성을 우회합니다.
"""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from jongji.config import settings
from jongji.database import get_db
from jongji.main import app
from jongji.models.enums import ProjectRole, TaskStatus, TeamRole
from jongji.models.project import Project, ProjectMember
from jongji.models.task import Task, TaskRelation
from jongji.models.team import Team, TeamMember
from jongji.models.user import User
from jongji.services.transition_service import (
    ALLOWED_TRANSITIONS,
    validate_transition,
)


def _hash_password(password: str) -> str:
    """테스트용 비밀번호 해싱."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _make_token(user_id: str) -> str:
    """테스트용 JWT 액세스 토큰을 생성합니다."""
    payload = {
        "sub": user_id,
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@pytest.fixture
async def client(db_session):
    """테스트용 AsyncClient 픽스처."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def trans_user(db_session) -> User:
    """테스트용 기본 사용자를 ORM으로 생성합니다."""
    user = User(
        email="transuser@example.com",
        name="Trans User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def trans_headers(trans_user) -> dict:
    """테스트용 인증 헤더."""
    token = _make_token(str(trans_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def trans_env(db_session, trans_user):
    """테스트용 팀/프로젝트 환경을 생성합니다."""
    team = Team(name="Trans Team", created_by=trans_user.id)
    db_session.add(team)
    await db_session.flush()

    tm = TeamMember(team_id=team.id, user_id=trans_user.id, role=TeamRole.LEADER)
    db_session.add(tm)
    await db_session.flush()

    project = Project(
        team_id=team.id,
        name="Trans Project",
        key="TRANS",
        owner_id=trans_user.id,
    )
    db_session.add(project)
    await db_session.flush()

    pm = ProjectMember(
        project_id=project.id,
        user_id=trans_user.id,
        role=ProjectRole.LEADER,
    )
    db_session.add(pm)
    await db_session.flush()

    return {"team": team, "project": project, "user": trans_user}


async def _create_task_orm(db_session, project, user, status=TaskStatus.BACKLOG) -> Task:
    """테스트용 작업을 ORM으로 직접 생성합니다."""
    from sqlalchemy import select

    from jongji.models.project import Project as Proj

    result = await db_session.execute(
        select(Proj).where(Proj.id == project.id).with_for_update()
    )
    proj = result.scalar_one()
    proj.task_counter += 1
    task = Task(
        project_id=project.id,
        number=proj.task_counter,
        title=f"Task {proj.task_counter}",
        status=status,
        priority=5,
        creator_id=user.id,
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Unit tests: validate_transition (pure function, no DB)
# ---------------------------------------------------------------------------


class TestAllowedTransitions:
    """ALLOWED_TRANSITIONS 테이블 검증."""

    def test_backlog_to_todo_allowed(self):
        """BACKLOG -> TODO 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.BACKLOG, TaskStatus.TODO) is True

    def test_todo_to_progress_allowed(self):
        """TODO -> PROGRESS 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.TODO, TaskStatus.PROGRESS) is True

    def test_todo_to_backlog_allowed(self):
        """TODO -> BACKLOG 후퇴 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.TODO, TaskStatus.BACKLOG) is True

    def test_progress_to_review_allowed(self):
        """PROGRESS -> REVIEW 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.PROGRESS, TaskStatus.REVIEW) is True

    def test_progress_to_todo_allowed(self):
        """PROGRESS -> TODO 후퇴 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.PROGRESS, TaskStatus.TODO) is True

    def test_review_to_done_allowed(self):
        """REVIEW -> DONE 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.REVIEW, TaskStatus.DONE) is True

    def test_review_to_progress_allowed(self):
        """REVIEW -> PROGRESS 후퇴 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.REVIEW, TaskStatus.PROGRESS) is True

    def test_done_to_closed_allowed(self):
        """DONE -> CLOSED 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.DONE, TaskStatus.CLOSED) is True

    def test_done_to_reopen_allowed(self):
        """DONE -> REOPEN 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.DONE, TaskStatus.REOPEN) is True

    def test_reopen_to_todo_allowed(self):
        """REOPEN -> TODO 전환이 허용됩니다."""
        assert validate_transition(TaskStatus.REOPEN, TaskStatus.TODO) is True

    def test_closed_no_transitions(self):
        """CLOSED 상태에서는 어떤 전환도 허용되지 않습니다."""
        for target in TaskStatus:
            if target != TaskStatus.CLOSED:
                assert validate_transition(TaskStatus.CLOSED, target) is False

    def test_skip_todo_to_done_rejected(self):
        """TODO -> DONE 건너뛰기 전환은 거부됩니다."""
        assert validate_transition(TaskStatus.TODO, TaskStatus.DONE) is False

    def test_skip_backlog_to_progress_rejected(self):
        """BACKLOG -> PROGRESS 건너뛰기 전환은 거부됩니다."""
        assert validate_transition(TaskStatus.BACKLOG, TaskStatus.PROGRESS) is False

    def test_skip_backlog_to_review_rejected(self):
        """BACKLOG -> REVIEW 건너뛰기 전환은 거부됩니다."""
        assert validate_transition(TaskStatus.BACKLOG, TaskStatus.REVIEW) is False

    def test_allowed_transitions_table_completeness(self):
        """ALLOWED_TRANSITIONS 테이블이 모든 상태를 포함합니다."""
        for status in TaskStatus:
            assert status in ALLOWED_TRANSITIONS


# ---------------------------------------------------------------------------
# Integration tests: PATCH /api/v1/tasks/{task_id}/status
# ---------------------------------------------------------------------------


class TestStatusTransitionAPI:
    """PATCH /api/v1/tasks/{task_id}/status 테스트."""

    async def test_valid_transition_backlog_to_todo(self, client, trans_headers, trans_env, db_session):
        """BACKLOG -> TODO 전환 성공 테스트."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.BACKLOG)
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "TODO"},
            headers=trans_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "TODO"

    async def test_valid_transition_todo_to_progress(self, client, trans_headers, trans_env, db_session):
        """TODO -> PROGRESS 전환 성공 테스트."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.TODO)
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "PROGRESS"},
            headers=trans_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PROGRESS"

    async def test_invalid_transition_todo_to_done(self, client, trans_headers, trans_env, db_session):
        """TODO -> DONE 건너뛰기 전환 거부 테스트 (422)."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.TODO)
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "DONE"},
            headers=trans_headers,
        )
        assert resp.status_code == 422

    async def test_invalid_transition_backlog_to_progress(self, client, trans_headers, trans_env, db_session):
        """BACKLOG -> PROGRESS 건너뛰기 전환 거부 테스트 (422)."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.BACKLOG)
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "PROGRESS"},
            headers=trans_headers,
        )
        assert resp.status_code == 422

    async def test_closed_no_transition(self, client, trans_headers, trans_env, db_session):
        """CLOSED 상태에서 전환 시도 거부 테스트 (422)."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.CLOSED)
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "TODO"},
            headers=trans_headers,
        )
        assert resp.status_code == 422

    async def test_task_not_found(self, client, trans_headers):
        """존재하지 않는 작업 상태 전환 시 404 테스트."""
        resp = await client.patch(
            f"/api/v1/tasks/{uuid.uuid4()}/status",
            json={"status": "TODO"},
            headers=trans_headers,
        )
        assert resp.status_code == 404

    async def test_unauthenticated(self, client, trans_env, db_session):
        """인증 없이 상태 전환 시도 시 401 테스트."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.BACKLOG)
        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "TODO"},
        )
        assert resp.status_code == 401

    async def test_progress_blocked_by_unfinished(self, client, trans_headers, trans_env, db_session):
        """PROGRESS 진입 시 미완료 blocked_by 작업이 있으면 422 테스트."""
        blocker = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.TODO)
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.TODO)

        # blocked_by 관계 설정
        relation = TaskRelation(task_id=task.id, blocked_by_task_id=blocker.id)
        db_session.add(relation)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "PROGRESS"},
            headers=trans_headers,
        )
        assert resp.status_code == 422

    async def test_progress_allowed_when_blocker_done(self, client, trans_headers, trans_env, db_session):
        """PROGRESS 진입 시 blocked_by가 DONE이면 성공 테스트."""
        blocker = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.DONE)
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.TODO)

        relation = TaskRelation(task_id=task.id, blocked_by_task_id=blocker.id)
        db_session.add(relation)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "PROGRESS"},
            headers=trans_headers,
        )
        assert resp.status_code == 200

    async def test_progress_allowed_when_blocker_closed(self, client, trans_headers, trans_env, db_session):
        """PROGRESS 진입 시 blocked_by가 CLOSED이면 성공 테스트."""
        blocker = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.CLOSED)
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"], TaskStatus.TODO)

        relation = TaskRelation(task_id=task.id, blocked_by_task_id=blocker.id)
        db_session.add(relation)
        await db_session.flush()

        resp = await client.patch(
            f"/api/v1/tasks/{task.id}/status",
            json={"status": "PROGRESS"},
            headers=trans_headers,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Integration tests: POST/DELETE /api/v1/tasks/{task_id}/relations
# ---------------------------------------------------------------------------


class TestRelationsAPI:
    """POST/DELETE /api/v1/tasks/{task_id}/relations 테스트."""

    async def test_add_relation_success(self, client, trans_headers, trans_env, db_session):
        """blocked_by 관계 추가 성공 테스트."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])
        blocker = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])

        resp = await client.post(
            f"/api/v1/tasks/{task.id}/relations",
            json={"blocked_by_task_id": str(blocker.id)},
            headers=trans_headers,
        )
        assert resp.status_code == 201

    async def test_add_relation_self_blocked(self, client, trans_headers, trans_env, db_session):
        """자기 자신을 blocked_by로 추가하면 422 테스트."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])

        resp = await client.post(
            f"/api/v1/tasks/{task.id}/relations",
            json={"blocked_by_task_id": str(task.id)},
            headers=trans_headers,
        )
        assert resp.status_code == 422

    async def test_add_relation_cycle_detection(self, client, trans_headers, trans_env, db_session):
        """사이클 감지 테스트: A -> B -> A 형성 시 422."""
        task_a = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])
        task_b = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])

        # A is blocked by B
        relation = TaskRelation(task_id=task_a.id, blocked_by_task_id=task_b.id)
        db_session.add(relation)
        await db_session.flush()

        # Try to make B blocked by A (cycle)
        resp = await client.post(
            f"/api/v1/tasks/{task_b.id}/relations",
            json={"blocked_by_task_id": str(task_a.id)},
            headers=trans_headers,
        )
        assert resp.status_code == 422

    async def test_add_relation_max_10(self, client, trans_headers, trans_env, db_session):
        """blocked_by 최대 10개 초과 시 422 테스트."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])

        # 10개까지 추가
        for _ in range(10):
            blocker = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])
            relation = TaskRelation(task_id=task.id, blocked_by_task_id=blocker.id)
            db_session.add(relation)
        await db_session.flush()

        # 11번째 추가 시도
        extra_blocker = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])
        resp = await client.post(
            f"/api/v1/tasks/{task.id}/relations",
            json={"blocked_by_task_id": str(extra_blocker.id)},
            headers=trans_headers,
        )
        assert resp.status_code == 422

    async def test_delete_relation_success(self, client, trans_headers, trans_env, db_session):
        """blocked_by 관계 삭제 성공 테스트."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])
        blocker = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])

        relation = TaskRelation(task_id=task.id, blocked_by_task_id=blocker.id)
        db_session.add(relation)
        await db_session.flush()

        resp = await client.delete(
            f"/api/v1/tasks/{task.id}/relations/{blocker.id}",
            headers=trans_headers,
        )
        assert resp.status_code == 204

    async def test_delete_relation_not_found(self, client, trans_headers, trans_env, db_session):
        """존재하지 않는 관계 삭제 시 404 테스트."""
        task = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])

        resp = await client.delete(
            f"/api/v1/tasks/{task.id}/relations/{uuid.uuid4()}",
            headers=trans_headers,
        )
        assert resp.status_code == 404

    async def test_add_relation_cycle_chain(self, client, trans_headers, trans_env, db_session):
        """사이클 감지 테스트: A -> B -> C -> A 체인 형성 시 422."""
        task_a = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])
        task_b = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])
        task_c = await _create_task_orm(db_session, trans_env["project"], trans_env["user"])

        # A blocked by B, B blocked by C
        db_session.add(TaskRelation(task_id=task_a.id, blocked_by_task_id=task_b.id))
        db_session.add(TaskRelation(task_id=task_b.id, blocked_by_task_id=task_c.id))
        await db_session.flush()

        # Try: C blocked by A (would form cycle)
        resp = await client.post(
            f"/api/v1/tasks/{task_c.id}/relations",
            json={"blocked_by_task_id": str(task_a.id)},
            headers=trans_headers,
        )
        assert resp.status_code == 422
