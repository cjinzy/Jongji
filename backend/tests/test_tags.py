"""태그 시스템 테스트 - TDD 방식.

태그 추출 정규식, 태그 동기화, 태그 API 엔드포인트를 테스트합니다.
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
from jongji.models.task import Task, TaskTag
from jongji.models.team import Team, TeamMember
from jongji.models.user import User
from jongji.services import tag_service


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
async def tag_user(db_session) -> User:
    """테스트용 사용자를 ORM으로 생성합니다."""
    user = User(
        email=f"taguser_{uuid.uuid4().hex[:8]}@example.com",
        name="Tag User",
        password_hash=_hash_password("password123"),
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def tag_headers(tag_user) -> dict:
    """테스트용 인증 헤더."""
    token = _make_token(str(tag_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def tag_env(db_session, tag_user):
    """테스트용 팀/프로젝트/작업 환경을 생성합니다."""
    team = Team(name=f"Tag Team {uuid.uuid4().hex[:4]}", created_by=tag_user.id)
    db_session.add(team)
    await db_session.flush()

    tm = TeamMember(team_id=team.id, user_id=tag_user.id, role=TeamRole.LEADER)
    db_session.add(tm)
    await db_session.flush()

    project = Project(
        team_id=team.id,
        name="Tag Project",
        key=f"TAG{uuid.uuid4().hex[:3].upper()}",
        owner_id=tag_user.id,
    )
    db_session.add(project)
    await db_session.flush()

    pm = ProjectMember(
        project_id=project.id,
        user_id=tag_user.id,
        role=ProjectRole.LEADER,
    )
    db_session.add(pm)
    await db_session.flush()

    return {"team": team, "project": project}


# ---------------------------------------------------------------------------
# Unit tests: extract_tags
# ---------------------------------------------------------------------------


class TestExtractTags:
    """tag_service.extract_tags() 단위 테스트."""

    def test_extract_single_tag(self):
        """단일 영문 태그 추출."""
        result = tag_service.extract_tags("Hello #world today")
        assert result == ["world"]

    def test_extract_multiple_tags(self):
        """여러 태그 추출."""
        result = tag_service.extract_tags("#bug fix for #feature")
        assert result == ["bug", "feature"]

    def test_extract_korean_tag(self):
        """한글 태그 추출."""
        result = tag_service.extract_tags("작업 #버그수정 필요")
        assert result == ["버그수정"]

    def test_extract_tag_with_underscore(self):
        """언더스코어 포함 태그 추출."""
        result = tag_service.extract_tags("Check #my_tag here")
        assert result == ["my_tag"]

    def test_extract_tag_with_hyphen(self):
        """하이픈 포함 태그 추출."""
        result = tag_service.extract_tags("Check #my-tag here")
        assert result == ["my-tag"]

    def test_extract_tag_with_numbers(self):
        """숫자 포함 태그 추출."""
        result = tag_service.extract_tags("Release #v2 now")
        assert result == ["v2"]

    def test_extract_no_tags(self):
        """태그 없는 텍스트 - 빈 목록 반환."""
        result = tag_service.extract_tags("No tags here")
        assert result == []

    def test_extract_deduplicates(self):
        """중복 태그 제거."""
        result = tag_service.extract_tags("#dup and again #dup")
        assert result == ["dup"]

    def test_extract_empty_string(self):
        """빈 문자열 - 빈 목록 반환."""
        result = tag_service.extract_tags("")
        assert result == []

    def test_extract_preserves_order(self):
        """첫 등장 순서 유지."""
        result = tag_service.extract_tags("#alpha #beta #gamma")
        assert result == ["alpha", "beta", "gamma"]


# ---------------------------------------------------------------------------
# Integration tests: sync_tags
# ---------------------------------------------------------------------------


class TestSyncTags:
    """tag_service.sync_tags() 통합 테스트."""

    async def test_sync_creates_tags(self, db_session, tag_env, tag_user):
        """작업 생성 시 태그가 task_tags에 저장됨."""
        project = tag_env["project"]
        task = Task(
            project_id=project.id,
            number=100,
            title="#sync test",
            status=TaskStatus.BACKLOG,
            priority=5,
            creator_id=tag_user.id,
        )
        db_session.add(task)
        await db_session.flush()

        await tag_service.sync_tags(task.id, "#sync test", None, db_session)

        from sqlalchemy import select
        result = await db_session.execute(
            select(TaskTag).where(TaskTag.task_id == task.id)
        )
        tags = result.scalars().all()
        assert len(tags) == 1
        assert tags[0].tag == "sync"

    async def test_sync_replaces_old_tags(self, db_session, tag_env, tag_user):
        """태그 업데이트 시 기존 태그를 모두 교체함."""
        project = tag_env["project"]
        task = Task(
            project_id=project.id,
            number=101,
            title="#old",
            status=TaskStatus.BACKLOG,
            priority=5,
            creator_id=tag_user.id,
        )
        db_session.add(task)
        await db_session.flush()

        await tag_service.sync_tags(task.id, "#old", None, db_session)
        await tag_service.sync_tags(task.id, "#new title", None, db_session)

        from sqlalchemy import select
        result = await db_session.execute(
            select(TaskTag).where(TaskTag.task_id == task.id)
        )
        tags = [t.tag for t in result.scalars().all()]
        assert "new" in tags
        assert "old" not in tags

    async def test_sync_merges_title_and_description(self, db_session, tag_env, tag_user):
        """제목과 설명의 태그를 합쳐서 저장 (중복 제거)."""
        project = tag_env["project"]
        task = Task(
            project_id=project.id,
            number=102,
            title="#title",
            description="#desc also #title",
            status=TaskStatus.BACKLOG,
            priority=5,
            creator_id=tag_user.id,
        )
        db_session.add(task)
        await db_session.flush()

        await tag_service.sync_tags(task.id, "#title", "#desc also #title", db_session)

        from sqlalchemy import select
        result = await db_session.execute(
            select(TaskTag).where(TaskTag.task_id == task.id)
        )
        tags = sorted([t.tag for t in result.scalars().all()])
        assert tags == ["desc", "title"]


# ---------------------------------------------------------------------------
# API tests: GET /api/v1/tags
# ---------------------------------------------------------------------------


class TestListTagsAPI:
    """GET /api/v1/tags?project_id={id} 테스트."""

    async def test_list_tags_empty(self, client, tag_headers, tag_env):
        """태그 없는 프로젝트 - 빈 목록 반환."""
        project_id = tag_env["project"].id
        resp = await client.get(
            f"/api/v1/tags?project_id={project_id}",
            headers=tag_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_tags_with_usage_count(self, client, tag_headers, tag_env):
        """태그 사용 횟수를 포함한 목록 반환."""
        project_id = tag_env["project"].id

        # 작업 2개 생성 (#bug 공통, #feature는 1개에만)
        await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={"title": "Fix #bug and #feature"},
            headers=tag_headers,
        )
        await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={"title": "Another #bug fix"},
            headers=tag_headers,
        )

        resp = await client.get(
            f"/api/v1/tags?project_id={project_id}",
            headers=tag_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        tags_by_name = {item["tag"]: item["count"] for item in data}
        assert tags_by_name["bug"] == 2
        assert tags_by_name["feature"] == 1

    async def test_list_tags_requires_project_id(self, client, tag_headers):
        """project_id 미제공 시 422 반환."""
        resp = await client.get("/api/v1/tags", headers=tag_headers)
        assert resp.status_code == 422

    async def test_list_tags_requires_auth(self, client, tag_env):
        """인증 없이 접근 시 401 반환."""
        project_id = tag_env["project"].id
        resp = await client.get(f"/api/v1/tags?project_id={project_id}")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# API tests: GET /api/v1/tags/{tag}/tasks
# ---------------------------------------------------------------------------


class TestGetTasksByTagAPI:
    """GET /api/v1/tags/{tag}/tasks?project_id={id} 테스트."""

    async def test_get_tasks_by_tag(self, client, tag_headers, tag_env):
        """특정 태그가 붙은 작업 목록 반환."""
        project_id = tag_env["project"].id

        await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={"title": "Task with #urgent tag"},
            headers=tag_headers,
        )
        await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={"title": "Another #urgent task"},
            headers=tag_headers,
        )
        await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={"title": "No matching tag here"},
            headers=tag_headers,
        )

        resp = await client.get(
            f"/api/v1/tags/urgent/tasks?project_id={project_id}",
            headers=tag_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["tasks"]) == 2

    async def test_get_tasks_by_tag_not_found(self, client, tag_headers, tag_env):
        """존재하지 않는 태그 - 빈 작업 목록 반환."""
        project_id = tag_env["project"].id
        resp = await client.get(
            f"/api/v1/tags/nonexistent/tasks?project_id={project_id}",
            headers=tag_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["tasks"] == []

    async def test_get_tasks_by_tag_requires_project_id(self, client, tag_headers):
        """project_id 미제공 시 422 반환."""
        resp = await client.get("/api/v1/tags/sometag/tasks", headers=tag_headers)
        assert resp.status_code == 422

    async def test_get_tasks_by_tag_requires_auth(self, client, tag_env):
        """인증 없이 접근 시 401 반환."""
        project_id = tag_env["project"].id
        resp = await client.get(f"/api/v1/tags/sometag/tasks?project_id={project_id}")
        assert resp.status_code == 401
