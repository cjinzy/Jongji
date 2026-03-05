"""Task Comment CRUD API 테스트 - TDD 방식.

댓글 생성, 조회, 수정, 삭제 및 @mention 추출/감시자 등록을 테스트합니다.
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
from jongji.models.task import Task, TaskWatcher
from jongji.models.team import Team, TeamMember
from jongji.models.user import User
from jongji.services.comment_service import extract_mentions


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
async def comment_user(db_session) -> User:
    """테스트용 작성자를 ORM으로 생성합니다."""
    user = User(
        email=f"comment_author_{uuid.uuid4().hex[:8]}@example.com",
        name="CommentAuthor",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session) -> User:
    """다른 테스트용 사용자 (관리자 아님)."""
    user = User(
        email=f"other_{uuid.uuid4().hex[:8]}@example.com",
        name="OtherUser",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session) -> User:
    """테스트용 관리자 사용자."""
    user = User(
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        name="AdminUser",
        password_hash=_hash_password("password123"),
        is_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def mention_target_user(db_session) -> User:
    """@mention 대상 사용자."""
    user = User(
        email=f"mention_{uuid.uuid4().hex[:8]}@example.com",
        name="MentionTarget",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def comment_env(db_session, comment_user):
    """테스트용 팀/프로젝트/작업 환경을 생성합니다."""
    team = Team(name=f"Comment Team {uuid.uuid4().hex[:6]}", created_by=comment_user.id)
    db_session.add(team)
    await db_session.flush()

    tm = TeamMember(team_id=team.id, user_id=comment_user.id, role=TeamRole.LEADER)
    db_session.add(tm)
    await db_session.flush()

    project = Project(
        team_id=team.id,
        name="Comment Project",
        key=f"CMT{uuid.uuid4().hex[:4].upper()}",
        owner_id=comment_user.id,
    )
    db_session.add(project)
    await db_session.flush()

    pm = ProjectMember(
        project_id=project.id,
        user_id=comment_user.id,
        role=ProjectRole.LEADER,
    )
    db_session.add(pm)
    await db_session.flush()

    task = Task(
        project_id=project.id,
        number=1,
        title="Comment Task",
        creator_id=comment_user.id,
        status=TaskStatus.BACKLOG,
        priority=5,
    )
    db_session.add(task)
    await db_session.flush()
    await db_session.refresh(task)

    return {"team": team, "project": project, "task": task}


class TestExtractMentions:
    """extract_mentions 유틸 함수 단위 테스트."""

    def test_single_mention(self):
        """단일 @mention 추출 테스트."""
        result = extract_mentions("안녕 @alice 잘 지내?")
        assert result == ["alice"]

    def test_multiple_mentions(self):
        """복수 @mention 추출 테스트."""
        result = extract_mentions("@alice @bob 모두 확인해주세요.")
        assert result == ["alice", "bob"]

    def test_duplicate_mention_dedup(self):
        """중복 @mention 제거 테스트."""
        result = extract_mentions("@alice @alice 두 번 언급")
        assert result == ["alice"]

    def test_no_mention(self):
        """@mention 없는 텍스트 테스트."""
        result = extract_mentions("mention 없는 텍스트")
        assert result == []

    def test_mention_with_dot(self):
        """점이 포함된 @mention 추출 테스트."""
        result = extract_mentions("@john.doe 확인해주세요")
        assert result == ["john.doe"]


class TestListComments:
    """GET /api/v1/tasks/{task_id}/comments 테스트."""

    async def test_list_comments_empty(self, client, comment_user, comment_env):
        """댓글 없는 작업의 목록은 빈 배열."""
        token = _make_token(str(comment_user.id))
        resp = await client.get(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_comments_after_create(self, client, comment_user, comment_env):
        """댓글 생성 후 목록 조회 테스트."""
        token = _make_token(str(comment_user.id))
        headers = {"Authorization": f"Bearer {token}"}
        task_id = comment_env["task"].id

        await client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "첫 번째 댓글"},
            headers=headers,
        )
        await client.post(
            f"/api/v1/tasks/{task_id}/comments",
            json={"content": "두 번째 댓글"},
            headers=headers,
        )

        resp = await client.get(f"/api/v1/tasks/{task_id}/comments", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["content"] == "첫 번째 댓글"
        assert data[1]["content"] == "두 번째 댓글"

    async def test_list_comments_task_not_found(self, client, comment_user):
        """존재하지 않는 작업의 댓글 목록 조회 시 404."""
        token = _make_token(str(comment_user.id))
        resp = await client.get(
            f"/api/v1/tasks/{uuid.uuid4()}/comments",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_list_comments_unauthenticated(self, client, comment_env):
        """인증 없이 조회 시 401."""
        resp = await client.get(f"/api/v1/tasks/{comment_env['task'].id}/comments")
        assert resp.status_code == 401


class TestCreateComment:
    """POST /api/v1/tasks/{task_id}/comments 테스트."""

    async def test_create_comment_success(self, client, comment_user, comment_env):
        """댓글 생성 성공 테스트."""
        token = _make_token(str(comment_user.id))
        resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "테스트 댓글입니다."},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "테스트 댓글입니다."
        assert data["user_id"] == str(comment_user.id)
        assert data["task_id"] == str(comment_env["task"].id)
        assert "id" in data
        assert "created_at" in data

    async def test_create_comment_empty_content_rejected(self, client, comment_user, comment_env):
        """빈 내용 댓글 생성 시 422 테스트."""
        token = _make_token(str(comment_user.id))
        resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": ""},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422

    async def test_create_comment_task_not_found(self, client, comment_user):
        """존재하지 않는 작업에 댓글 생성 시 404."""
        token = _make_token(str(comment_user.id))
        resp = await client.post(
            f"/api/v1/tasks/{uuid.uuid4()}/comments",
            json={"content": "없는 작업에 댓글"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_create_comment_unauthenticated(self, client, comment_env):
        """인증 없이 댓글 생성 시 401."""
        resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "인증 없는 댓글"},
        )
        assert resp.status_code == 401

    async def test_create_comment_with_mention_adds_watcher(
        self, client, comment_user, comment_env, mention_target_user, db_session
    ):
        """@mention 댓글 생성 시 대상 사용자가 감시자로 등록됩니다."""
        token = _make_token(str(comment_user.id))
        resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": f"@{mention_target_user.name} 확인해주세요."},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201

        from sqlalchemy import select as sa_select
        watcher_result = await db_session.execute(
            sa_select(TaskWatcher).where(
                TaskWatcher.task_id == comment_env["task"].id,
                TaskWatcher.user_id == mention_target_user.id,
            )
        )
        watcher = watcher_result.scalar_one_or_none()
        assert watcher is not None

    async def test_create_comment_mention_unknown_user_ignored(
        self, client, comment_user, comment_env
    ):
        """존재하지 않는 사용자 @mention은 무시되고 댓글은 정상 생성됩니다."""
        token = _make_token(str(comment_user.id))
        resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "@nonexistentuser123 확인해주세요."},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201


class TestUpdateComment:
    """PUT /api/v1/comments/{comment_id} 테스트."""

    async def test_update_comment_success(self, client, comment_user, comment_env):
        """작성자가 댓글을 수정하는 테스트."""
        token = _make_token(str(comment_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "원래 내용"},
            headers=headers,
        )
        comment_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/comments/{comment_id}",
            json={"content": "수정된 내용"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "수정된 내용"

    async def test_update_comment_forbidden_by_other_user(
        self, client, comment_user, other_user, comment_env
    ):
        """다른 사용자가 댓글 수정 시 403."""
        author_token = _make_token(str(comment_user.id))
        other_token = _make_token(str(other_user.id))

        create_resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "작성자 댓글"},
            headers={"Authorization": f"Bearer {author_token}"},
        )
        comment_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/comments/{comment_id}",
            json={"content": "다른 사람이 수정 시도"},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403

    async def test_update_comment_not_found(self, client, comment_user):
        """존재하지 않는 댓글 수정 시 404."""
        token = _make_token(str(comment_user.id))
        resp = await client.put(
            f"/api/v1/comments/{uuid.uuid4()}",
            json={"content": "수정"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_update_comment_unauthenticated(self, client, comment_user, comment_env):
        """인증 없이 댓글 수정 시 401."""
        token = _make_token(str(comment_user.id))
        create_resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "원래 내용"},
            headers={"Authorization": f"Bearer {token}"},
        )
        comment_id = create_resp.json()["id"]

        resp = await client.put(
            f"/api/v1/comments/{comment_id}",
            json={"content": "수정"},
        )
        assert resp.status_code == 401


class TestDeleteComment:
    """DELETE /api/v1/comments/{comment_id} 테스트."""

    async def test_delete_comment_by_author(self, client, comment_user, comment_env):
        """작성자가 댓글 삭제 성공."""
        token = _make_token(str(comment_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "삭제할 댓글"},
            headers=headers,
        )
        comment_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/comments/{comment_id}", headers=headers)
        assert resp.status_code == 204

    async def test_delete_comment_by_admin(
        self, client, comment_user, admin_user, comment_env
    ):
        """관리자가 다른 사람의 댓글 삭제 가능."""
        author_token = _make_token(str(comment_user.id))
        admin_token = _make_token(str(admin_user.id))

        create_resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "관리자가 삭제할 댓글"},
            headers={"Authorization": f"Bearer {author_token}"},
        )
        comment_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/comments/{comment_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 204

    async def test_delete_comment_forbidden_by_other_user(
        self, client, comment_user, other_user, comment_env
    ):
        """다른 비관리자 사용자가 댓글 삭제 시 403."""
        author_token = _make_token(str(comment_user.id))
        other_token = _make_token(str(other_user.id))

        create_resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "삭제 대상 댓글"},
            headers={"Authorization": f"Bearer {author_token}"},
        )
        comment_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/comments/{comment_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403

    async def test_delete_comment_not_found(self, client, comment_user):
        """존재하지 않는 댓글 삭제 시 404."""
        token = _make_token(str(comment_user.id))
        resp = await client.delete(
            f"/api/v1/comments/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_delete_comment_unauthenticated(self, client, comment_user, comment_env):
        """인증 없이 댓글 삭제 시 401."""
        token = _make_token(str(comment_user.id))
        create_resp = await client.post(
            f"/api/v1/tasks/{comment_env['task'].id}/comments",
            json={"content": "삭제 대상"},
            headers={"Authorization": f"Bearer {token}"},
        )
        comment_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/comments/{comment_id}")
        assert resp.status_code == 401
